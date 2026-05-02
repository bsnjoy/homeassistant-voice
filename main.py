#!/usr/bin/env python
import sys
import time
import os
import datetime
import socket
import subprocess
import numpy as np
import signal
from threading import Thread, Event
from collections import deque
from queue import Queue, Empty

import config
from utils import audio
from utils import stt
from utils import tts
from utils import homeassistant
from utils import ai

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

DEDUPE_WINDOW_SEC = getattr(config, "DEDUPE_WINDOW_SEC", 2.0)
TRANSCRIPTS_DIR = getattr(config, "TRANSCRIPTS_DIR", "transcripts")
# If a source delivers no audio chunks for this long, kill its subprocess so
# the supervisor can respawn it. Picked to be much larger than a normal read
# interval (chunks arrive every ~50 ms) but short enough that a frozen RTSP
# connection is recovered in well under a minute.
STALE_CHUNK_TIMEOUT_SEC = getattr(config, "STALE_CHUNK_TIMEOUT_SEC", 30.0)
SUBPROCESS_RESTART_DELAY_SEC = 2.0
WATCHDOG_NOTIFY_INTERVAL_SEC = 5.0


def sd_notify(message):
    """Send a message to systemd via $NOTIFY_SOCKET. No-op if unset."""
    addr = os.environ.get("NOTIFY_SOCKET")
    if not addr:
        return
    if addr.startswith("@"):
        addr = "\0" + addr[1:]
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.connect(addr)
            sock.sendall(message.encode())
    except Exception as e:
        print(f"sd_notify failed: {e}")


def append_transcript(source_name, ts, transcript):
    """Append one transcript line to transcripts/<source_name>.log."""
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    path = os.path.join(TRANSCRIPTS_DIR, f"{source_name}.log")
    iso = datetime.datetime.fromtimestamp(ts).astimezone().isoformat(timespec="milliseconds")
    text = (transcript or "").replace("\n", " ").replace("\r", " ").strip()
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{iso}\t{text}\n")


class SpeechSource(Thread):
    """One audio input (subprocess writing raw s16le to stdout).

    Reads chunks, detects speech by dB threshold, collects the utterance
    with pre-roll, transcribes it, and pushes (source_name, ts, transcript)
    onto a shared result queue. Runs one instance per microphone so that
    multiple sources are processed concurrently.
    """

    def __init__(self, name, cmd, result_queue, chunk_duration=0.05):
        super().__init__(daemon=True, name=f"SpeechSource[{name}]")
        self.source_name = name
        self.cmd = cmd
        self.result_queue = result_queue
        self.chunk_samples = int(config.SAMPLE_RATE * chunk_duration)
        self.chunk_size = self.chunk_samples * config.SAMPLE_WIDTH
        self.preroll_maxlen = max(1, int(config.PREROLL_DURATION_SEC / chunk_duration))
        self.stop_event = Event()
        self.process = None
        self.last_chunk_time = time.time()

    def run(self):
        while not self.stop_event.is_set():
            self._run_once()
            if self.stop_event.is_set():
                break
            print(
                f"[{self.source_name}] subprocess exited, restarting in "
                f"{SUBPROCESS_RESTART_DELAY_SEC:.0f}s"
            )
            self.stop_event.wait(SUBPROCESS_RESTART_DELAY_SEC)
            self.last_chunk_time = time.time()

    def _run_once(self):
        print(f"[{self.source_name}] starting audio source")
        try:
            self.process = subprocess.Popen(
                self.cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            )
        except Exception as e:
            print(f"[{self.source_name}] failed to start: {e}")
            return

        preroll = deque(maxlen=self.preroll_maxlen)
        recording = bytearray()
        is_recording = False
        silence_start = None

        try:
            while not self.stop_event.is_set():
                chunk = self.process.stdout.read(self.chunk_size)
                if not chunk:
                    print(f"[{self.source_name}] audio stream ended")
                    break
                self.last_chunk_time = time.time()

                samples = np.frombuffer(chunk, dtype=np.int16)
                db = audio.db_from_rms(audio.rms_from_samples(samples))
                now = self.last_chunk_time

                if db >= config.DB_THRESHOLD:
                    if not is_recording:
                        print(f"[{self.source_name}] speech detected ({db:.1f} dB)")
                        is_recording = True
                        recording = bytearray()
                        for c in preroll:
                            recording.extend(c)
                    recording.extend(chunk)
                    silence_start = None
                elif is_recording:
                    recording.extend(chunk)
                    if silence_start is None:
                        silence_start = now
                    elif (now - silence_start) * 1000 >= config.SILENCE_THRESHOLD_MS:
                        length_sec = len(recording) / (config.SAMPLE_RATE * config.SAMPLE_WIDTH)
                        print(f"[{self.source_name}] silence detected, length {length_sec:.2f}s")
                        if length_sec >= config.MIN_RECORDING_LENGTH_SEC:
                            transcript = stt.transcribe(bytes(recording))
                            print(f"[{self.source_name}] transcript: {transcript}")
                            append_transcript(self.source_name, now, transcript)
                            if transcript:
                                self.result_queue.put((self.source_name, now, transcript))
                        else:
                            print(f"[{self.source_name}] recording too short, discarding")
                        is_recording = False
                        silence_start = None
                        recording = bytearray()
                else:
                    preroll.append(chunk)
        except Exception as e:
            print(f"[{self.source_name}] error: {e}")
        finally:
            self._kill_process()

    def _kill_process(self):
        if not self.process:
            return
        try:
            self.process.terminate()
            try:
                self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
        except Exception:
            pass
        self.process = None

    def kill_subprocess(self):
        """Kill the running subprocess; the run() loop will respawn it."""
        proc = self.process
        if not proc:
            return
        try:
            proc.kill()
        except Exception:
            pass

    def stop(self):
        self.stop_event.set()
        self._kill_process()


def get_audio_sources():
    """Resolve the configured audio sources as a list of (name, cmd) tuples.

    Accepts either config.AUDIO_RECORD_CMDS (dict {name: cmd} or list of cmds)
    or the single-mic config.AUDIO_RECORD_CMD.
    """
    if hasattr(config, "AUDIO_RECORD_CMDS"):
        cmds = config.AUDIO_RECORD_CMDS
        if isinstance(cmds, dict):
            return list(cmds.items())
        return [(f"mic{i + 1}", cmd) for i, cmd in enumerate(cmds)]
    return [("mic", config.AUDIO_RECORD_CMD)]


def entity_key(entity_id):
    """Hashable key for dedupe — tuples for lists, strings pass through."""
    if isinstance(entity_id, (list, tuple)):
        return tuple(entity_id)
    return entity_id


def is_running_as_service():
    return "INVOCATION_ID" in os.environ or "JOURNAL_STREAM" in os.environ


sources = []


def signal_handler(sig, frame):
    signal_name = signal.Signals(sig).name
    print(f"\nReceived {signal_name} signal. Shutting down gracefully...")
    for s in sources:
        s.stop()
    for s in sources:
        s.join(timeout=2.0)
    tts.stop_tts_player_thread()
    print("Shutdown complete")
    sys.exit(0)


def stale_source_watchdog(srcs, stop_event):
    """Kill any source whose ffmpeg has stopped delivering chunks.

    The SpeechSource.run() loop respawns the subprocess after a kill, so this
    is what gets us out of the half-open-TCP wedge that follows a router
    reboot or upstream cable yank.
    """
    while not stop_event.wait(5.0):
        now = time.time()
        for s in srcs:
            stale = now - s.last_chunk_time
            if stale > STALE_CHUNK_TIMEOUT_SEC:
                print(
                    f"[{s.source_name}] no chunks for {stale:.0f}s "
                    f"(>{STALE_CHUNK_TIMEOUT_SEC:.0f}s) — killing subprocess"
                )
                s.kill_subprocess()
                s.last_chunk_time = now  # don't kill again before respawn settles


def systemd_watchdog_pinger(stop_event):
    """Periodic WATCHDOG=1 to systemd. Independent of source health on
    purpose — per-source recovery is handled internally; this is the safety
    net for the whole process being wedged."""
    if not os.environ.get("NOTIFY_SOCKET"):
        return
    while not stop_event.wait(WATCHDOG_NOTIFY_INTERVAL_SEC):
        sd_notify("WATCHDOG=1")


def main():
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    running_as_service = is_running_as_service()
    print("Speech Detection and Transcription System")
    print("Running as a systemd service" if running_as_service else "Running as a standalone application")
    print(f"Speech threshold: {config.DB_THRESHOLD} dB, Silence threshold: {config.SILENCE_THRESHOLD_MS} ms")
    print(f"Dedupe window: {DEDUPE_WINDOW_SEC} s")

    result_queue = Queue()
    for name, cmd in get_audio_sources():
        src = SpeechSource(name, cmd, result_queue)
        src.start()
        sources.append(src)
    print(f"Started {len(sources)} audio source(s): {', '.join(s.source_name for s in sources)}")

    watchdog_stop = Event()
    Thread(target=stale_source_watchdog, args=(sources, watchdog_stop),
           daemon=True, name="StaleSourceWatchdog").start()
    Thread(target=systemd_watchdog_pinger, args=(watchdog_stop,),
           daemon=True, name="SystemdWatchdog").start()
    sd_notify("READY=1")

    # (entity_key, action) -> timestamp of last successful execution
    last_executed = {}

    try:
        while True:
            try:
                source_name, ts, transcript = result_queue.get(timeout=1.0)
            except Empty:
                continue

            success, entity_id, action = homeassistant.process_command(transcript, source_name)
            if success:
                key = (entity_key(entity_id), action)
                now = time.time()
                prev = last_executed.get(key)
                if prev is not None and (now - prev) < DEDUPE_WINDOW_SEC:
                    print(
                        f"[{source_name}] dedupe: {action} {entity_id} already executed "
                        f"{now - prev:.2f}s ago, skipping"
                    )
                    continue
                last_executed[key] = now
                audio.play_audio(config.HOMEASSISTANT_SOUND)
                homeassistant.send_homeassistant_command(entity_id, action)
            elif ai.is_ai_command(transcript):
                audio.play_audio(config.AI_SOUND)
                ai.process_ai_command(transcript)
    except KeyboardInterrupt:
        print("\nExiting")
        for s in sources:
            s.stop()
        for s in sources:
            s.join(timeout=1.0)
        tts.stop_tts_player_thread()
        sys.exit(0)


if __name__ == "__main__":
    main()
