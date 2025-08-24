#!/usr/bin/env python3
import sys
import os
import time

# Add parent directory to path to import from utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.tts import play_tts_response, is_playing, stop_playing

# Test the play_tts_response function with a sample text
print("Starting TTS playback...")
process_handle = play_tts_response("Это тестовое сообщение для проверки сохранения аудио файла.")
print(f"Process handle: {process_handle}")

# Check if the audio is playing
if process_handle:
    print("Checking if audio is playing...")
    
    # Wait for a moment and check if it's still playing
    time.sleep(1)
    playing = is_playing(process_handle)
    print(f"Is audio still playing? {playing}")
    
    # Demonstrate how to do other work while audio is playing
    print("We can do other work while the audio is playing...")
    
    # Example: Let it play for a few seconds
    wait_time = 3
    print(f"Waiting for {wait_time} seconds...")
    time.sleep(wait_time)
    
    # Check again if it's still playing
    playing = is_playing(process_handle)
    print(f"Is audio still playing after {wait_time} seconds? {playing}")
    
    # Demonstrate how to stop the audio playback
    if playing:
        print("Stopping audio playback...")
        stop_result = stop_playing(process_handle)
        print(f"Stop result: {stop_result}")
        
        # Verify that it's stopped
        time.sleep(0.5)
        playing = is_playing(process_handle)
        print(f"Is audio still playing after stopping? {playing}")
    else:
        print("Audio playback already completed naturally.")
else:
    print("Failed to start TTS playback.")
