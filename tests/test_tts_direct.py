#!/usr/bin/env python3
import sys
import os
import time

# Add parent directory to path to import from utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.tts import _play_tts_segment, is_playing, stop_playing

# Test the direct TTS playback function (bypassing the queue)
print("Testing direct TTS playback (bypassing queue)...")
print("=" * 50)

# Test the _play_tts_segment function directly
text = "Это прямое тестовое сообщение без использования очереди."
print(f"Playing text: {text}")

process_handle = _play_tts_segment(text)
print(f"Process handle: {process_handle}")

if process_handle:
    print("\nChecking if audio is playing...")
    
    # Initial check
    playing = is_playing(process_handle)
    print(f"Is audio playing immediately after start? {playing}")
    
    # Wait for a moment and check again
    time.sleep(1)
    playing = is_playing(process_handle)
    print(f"Is audio still playing after 1 second? {playing}")
    
    # Demonstrate how to do other work while audio is playing
    print("\nDemonstrating concurrent work while audio plays...")
    for i in range(3):
        time.sleep(0.5)
        playing = is_playing(process_handle)
        print(f"  Step {i+1}: Audio still playing? {playing}")
    
    # Test stopping the audio
    if is_playing(process_handle):
        print("\nTesting stop functionality...")
        stop_result = stop_playing(process_handle)
        print(f"Stop command issued successfully: {stop_result}")
        
        # Verify that it's stopped
        time.sleep(0.5)
        playing = is_playing(process_handle)
        print(f"Is audio still playing after stop command? {playing}")
    else:
        print("\nAudio playback completed naturally.")
    
    # Test with a longer text
    print("\n" + "=" * 50)
    print("Testing with longer text...")
    long_text = "Это более длинное сообщение для проверки. Оно содержит несколько предложений. Это позволит нам проверить, как работает воспроизведение более длинного текста."
    
    process_handle2 = _play_tts_segment(long_text)
    if process_handle2:
        print("Long text playback started successfully.")
        
        # Monitor playback
        start_time = time.time()
        while is_playing(process_handle2):
            elapsed = time.time() - start_time
            print(f"  Playing... ({elapsed:.1f}s)", end='\r')
            time.sleep(0.2)
        
        total_time = time.time() - start_time
        print(f"\nPlayback completed in {total_time:.1f} seconds.")
    else:
        print("Failed to start long text playback.")
else:
    print("Failed to start TTS playback.")

print("\nDirect TTS test completed.")
