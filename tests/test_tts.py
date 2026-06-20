#!/usr/bin/env python3
import sys
import os
import time

# Add parent directory to path to import from utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Manual TTS integration script (needs a deployment config.py, the TTS server
# and audio output). Guard the import so unittest discovery can import this
# module without erroring; the playback below only runs when executed directly.
try:
    from utils.tts import play_tts_response, stop_tts_player_thread, tts_queue, tts_lock, current_playing_process
    _DEPS_OK = True
    _DEPS_ERROR = None
except Exception as _exc:
    _DEPS_OK = False
    _DEPS_ERROR = _exc


def main():
    # Test the play_tts_response function with a sample text
    print("Starting TTS playback...")
    success = play_tts_response("Это тестовое сообщение для проверки сохранения аудио файла.")
    print(f"TTS queued successfully: {success}")

    if success:
        print("Checking TTS queue and playback status...")

        # Give the player thread a moment to start processing
        time.sleep(0.5)

        # Check if there's a current playing process
        with tts_lock:
            is_playing = current_playing_process is not None
        print(f"Is audio currently playing? {is_playing}")

        # Check queue size
        queue_size = tts_queue.qsize()
        print(f"Items in TTS queue: {queue_size}")

        # Demonstrate how to do other work while audio is playing
        print("We can do other work while the audio is playing...")

        # Example: Let it play for a few seconds
        wait_time = 3
        print(f"Waiting for {wait_time} seconds...")
        time.sleep(wait_time)

        # Check again if it's still playing
        with tts_lock:
            is_playing = current_playing_process is not None
        print(f"Is audio still playing after {wait_time} seconds? {is_playing}")

        # Add another TTS message to the queue to test sequential playback
        print("\nAdding another TTS message to the queue...")
        success2 = play_tts_response("Это второе сообщение для проверки последовательного воспроизведения.")
        print(f"Second TTS queued successfully: {success2}")

        # Check queue size again
        queue_size = tts_queue.qsize()
        print(f"Items in TTS queue after adding second message: {queue_size}")

        # Wait a bit more
        print(f"\nWaiting for both messages to complete...")
        time.sleep(5)

        # Check final status
        with tts_lock:
            is_playing = current_playing_process is not None
        queue_size = tts_queue.qsize()
        print(f"Is audio still playing? {is_playing}")
        print(f"Items remaining in TTS queue: {queue_size}")

        # Demonstrate how to stop the TTS player thread
        print("\nStopping TTS player thread...")
        stop_result = stop_tts_player_thread()
        print(f"TTS player thread stopped successfully: {stop_result}")
    else:
        print("Failed to queue TTS playback.")


if __name__ == "__main__":
    if not _DEPS_OK:
        print(f"SKIP: TTS dependencies unavailable ({_DEPS_ERROR})")
        sys.exit(0)
    main()
