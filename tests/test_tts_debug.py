#!/usr/bin/env python3
"""Test script for the new TTS provider with debug mode"""

import sys
import os
import time

# Add parent directory to path to import from utils and config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Manual TTS integration script: needs a deployment config.py, the TTS server
# and audio output. Guard the imports so unittest discovery can import this
# module without erroring; the body only runs when executed directly.
try:
    import config
    from utils.tts import play_tts_response, stop_tts_player_thread
    _DEPS_OK = True
    _DEPS_ERROR = None
except Exception as _exc:
    _DEPS_OK = False
    _DEPS_ERROR = _exc


def test_tts_with_debug():
    print("Testing TTS with debug mode...")
    
    # First test with DELETE_TTS_FILES = False
    print("\n1. Testing with DELETE_TTS_FILES = False (files will be kept)")
    config.DELETE_TTS_FILES = False
    
    test_text = "This is a test with debug mode enabled."
    print(f"Sending text: {test_text}")
    
    success = play_tts_response(test_text)
    
    if success:
        print("TTS queued successfully")
        time.sleep(3)
    else:
        print("Failed to queue TTS")
    
    # Now test with DELETE_TTS_FILES = True
    print("\n2. Testing with DELETE_TTS_FILES = True (files will be deleted)")
    config.DELETE_TTS_FILES = True
    
    test_text = "This is a test with normal mode."
    print(f"Sending text: {test_text}")
    
    success = play_tts_response(test_text)
    
    if success:
        print("TTS queued successfully")
        time.sleep(3)
    else:
        print("Failed to queue TTS")
    
    # Stop the player thread
    stop_tts_player_thread()
    print("\nTest completed")
    
    # List any remaining temp files
    import tempfile
    temp_dir = tempfile.gettempdir()
    wav_files = [f for f in os.listdir(temp_dir) if f.endswith('.wav')]
    if wav_files:
        print(f"\nRemaining WAV files in temp directory ({temp_dir}):")
        for f in wav_files[:5]:  # Show first 5 files
            print(f"  - {f}")
    else:
        print("\nNo WAV files found in temp directory (all cleaned up)")

if __name__ == "__main__":
    if not _DEPS_OK:
        print(f"SKIP: TTS dependencies unavailable ({_DEPS_ERROR})")
        sys.exit(0)
    test_tts_with_debug()
