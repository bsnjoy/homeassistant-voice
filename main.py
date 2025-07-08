#!/usr/bin/env python
import sys
import time
import os
import datetime
import numpy as np
import signal
from threading import Thread, Event, Lock
from collections import deque
import config
from utils import audio
from utils import stt
from utils import tts
from utils import homeassistant
from utils import ai

# Force stdout and stderr to be unbuffered to ensure logs appear immediately in systemd journal
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

class AudioCaptureThread(Thread):
    """Thread class for capturing audio continuously in the background using a ring buffer."""
    
    def __init__(self, buffer_duration=10.0, chunk_duration=0.05):
        """
        Initialize the audio capture thread with a ring buffer.
        
        Parameters:
        - buffer_duration: Total duration of the ring buffer in seconds
        - chunk_duration: Duration of each audio chunk in seconds
        """
        Thread.__init__(self, daemon=True)
        self.chunk_size = int(config.SAMPLE_RATE * chunk_duration) * config.SAMPLE_WIDTH
        self.buffer_size = int(buffer_duration / chunk_duration)  # Number of chunks to store
        
        # Ring buffer to store audio data with timestamps
        self.buffer = deque(maxlen=self.buffer_size)
        self.buffer_lock = Lock()  # Lock for thread-safe buffer access
        
        # Event to signal thread to stop
        self.stop_event = Event()
        self.process = None
        
        # For volume level display
        self.current_db = -100
        self.is_recording = False
    
    def run(self):
        """Main method to run the thread."""
        self.process = audio.get_audio_stream()
        
        try:
            while not self.stop_event.is_set():
                # Read chunk of audio data
                audio_data = self.process.stdout.read(self.chunk_size)
                if len(audio_data) == 0:
                    break
                
                # Get current timestamp
                current_time = time.time()
                
                # Calculate audio metrics for monitoring
                samples = np.frombuffer(audio_data, dtype=np.int16)
                rms = audio.rms_from_samples(samples)
                db = audio.db_from_rms(rms)
                self.current_db = db
                
                # Add to ring buffer with timestamp
                with self.buffer_lock:
                    self.buffer.append((current_time, audio_data, db))
                
                # Small sleep to prevent CPU hogging
                time.sleep(0.001)
                
        except Exception as e:
            print(f"Error in audio capture thread: {e}")
        finally:
            if self.process:
                self.process.terminate()
    
    def get_audio_segment(self, start_time, end_time=None):
        """
        Extract audio segment from the ring buffer based on timestamps.
        
        Parameters:
        - start_time: Start timestamp for the segment
        - end_time: End timestamp for the segment (defaults to current time)
        
        Returns:
        - bytearray containing the audio segment
        """
        if end_time is None:
            end_time = time.time()
        
        segment = bytearray()
        
        with self.buffer_lock:
            # Make a copy to avoid modifying during iteration
            buffer_copy = list(self.buffer)
        
        # Extract chunks that fall within the time range
        for timestamp, data, _ in buffer_copy:
            if start_time <= timestamp <= end_time:
                segment.extend(data)
        
        return segment
    
    def get_current_db(self):
        """Get the current decibel level."""
        return self.current_db
    
    def set_recording_state(self, is_recording):
        """Set the recording state for display purposes."""
        self.is_recording = is_recording
    
    def get_recording_state(self):
        """Get the current recording state."""
        return self.is_recording
    
    def stop(self):
        """Signal the thread to stop."""
        self.stop_event.set()
        if self.process:
            self.process.terminate()


def process_audio_and_detect_speech(capture_thread, show_volume=True):
    """
    Process audio from the capture thread, detect speech, and transcribe when appropriate.
    Returns when a complete transcription cycle is done or no speech is detected.
    
    Parameters:
    - capture_thread: The AudioCaptureThread instance
    - show_volume: Whether to display the volume meter
    
    Returns:
    - transcript: The transcribed text if successful, None otherwise
    """
    # Initialize variables
    is_recording = False
    silence_start_time = None
    speech_start_time = None
    
    # For display updates
    last_display_time = time.time()
    display_interval = 0.1  # Update display every 100ms
    
    try:
        while True:
            # Get current dB level from capture thread
            current_db = capture_thread.get_current_db()
            
            # Update display at regular intervals if enabled
            current_time = time.time()
            if show_volume and current_time - last_display_time >= display_interval:
                audio.display_volume(current_db, is_recording)
                last_display_time = current_time
            
            # Check if we're above the threshold
            if current_db >= config.DB_THRESHOLD:
                if not is_recording:
                    print("\nSpeech detected, recording...")
                    is_recording = True
                    capture_thread.set_recording_state(True)
                    
                    # Set speech start time with preroll
                    speech_start_time = current_time - config.PREROLL_DURATION_SEC
                
                # Reset silence timer
                silence_start_time = None
            
            # If we're recording and below threshold, check for silence duration
            elif is_recording:
                if silence_start_time is None:
                    silence_start_time = current_time
                elif (current_time - silence_start_time) * 1000 >= config.SILENCE_THRESHOLD_MS:
                    # Silence duration exceeded threshold, stop recording
                    
                    # Extract the complete audio segment from the buffer
                    recorded_audio = capture_thread.get_audio_segment(speech_start_time, current_time)
                    recording_length_sec = len(recorded_audio) / (config.SAMPLE_RATE * config.SAMPLE_WIDTH)
                    
                    silence_end_time = time.time()
                    silence_detection_time = (silence_end_time - silence_start_time) * 1000
                    print(f"\nSilence detected, recording length: {recording_length_sec:.2f} seconds")
                    print(f"1. Period after speech ended (silence detection): {silence_detection_time:.2f} ms")
                    
                    if recording_length_sec >= config.MIN_RECORDING_LENGTH_SEC:
                        # Check if we should save to disk or process from memory
                        if config.SAVE_RECORDINGS_TO_DISK:
                            # Save to disk then transcribe
                            saved_path = audio.save_audio_to_file(recorded_audio)
                            print(f"Saved recording to {saved_path}")
                            transcript = stt.transcribe(saved_path)
                        else:
                            # Transcribe directly from memory
                            print("Processing recording from memory (not saved to disk)")
                            transcript = stt.transcribe(recorded_audio)
                        
                        print(f"Transcript: {transcript}")
                        
                        # Reset recording state
                        is_recording = False
                        capture_thread.set_recording_state(False)
                        
                        # Return the transcript
                        return transcript
                    else:
                        print("Recording too short, discarding")
                    
                    # Reset recording state
                    is_recording = False
                    capture_thread.set_recording_state(False)
                    speech_start_time = None
                    silence_start_time = None
            
            # Small sleep to prevent CPU hogging
            time.sleep(0.01)
                
    except KeyboardInterrupt:
        pass
    
    return None


def is_running_as_service():
    """Check if the program is running as a systemd service."""
    # Check for INVOCATION_ID environment variable which is set by systemd
    return 'INVOCATION_ID' in os.environ or 'JOURNAL_STREAM' in os.environ

def signal_handler(sig, frame):
    """Handle signals like SIGTERM for graceful shutdown."""
    print("\nReceived signal to terminate. Shutting down gracefully...")
    if 'capture_thread' in globals():
        globals()['capture_thread'].stop()
        globals()['capture_thread'].join(timeout=1.0)
    
    # Stop the TTS player thread
    tts.stop_tts_player_thread()
    
    sys.exit(0)

def main():
    """Main function to run the speech detection and transcription system."""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Check if running as a service
    running_as_service = is_running_as_service()
    
    print(f"Speech Detection and Transcription System")
    if running_as_service:
        print("Running as a systemd service")
    else:
        print("Running as a standalone application")
    print(f"Speech threshold: {config.DB_THRESHOLD} dB, Silence threshold: {config.SILENCE_THRESHOLD_MS} ms")
    if not running_as_service:
        print("Press Ctrl+C to exit")
    
    # Create and start capture thread with ring buffer
    # Buffer 10 seconds of audio (adjust as needed)
    global capture_thread  # Make it accessible to signal handler
    capture_thread = AudioCaptureThread(buffer_duration=10.0, chunk_duration=0.05)
    capture_thread.start()
    
    print("Audio capture thread started with ring buffer")
    
    try:
        while True:
            transcript = process_audio_and_detect_speech(capture_thread, show_volume=not running_as_service)
            if transcript:                
                success, entity_id, action = homeassistant.process_command(transcript)
                if success:
                    audio.play_audio(config.HOMEASSISTANT_SOUND)
                    # Call send_homeassistant_command with the returned values
                    homeassistant.send_homeassistant_command(entity_id, action)
                elif ai.is_ai_command(transcript):
                    audio.play_audio(config.AI_SOUND)
                    # The process_ai_command now handles streaming and TTS directly
                    ai.process_ai_command(transcript)
                    
                    # No need to wait here as the TTS is handled by the background thread
    except KeyboardInterrupt:
        print("\nExiting")
        # Stop the capture thread
        capture_thread.stop()
        capture_thread.join(timeout=1.0)
        
        # Stop the TTS player thread
        tts.stop_tts_player_thread()
        
        sys.exit(0)

if __name__ == "__main__":
    main()
