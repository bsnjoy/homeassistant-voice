# TTS Testing Documentation

## Overview

The TTS (Text-to-Speech) system has been refactored to use a queue-based architecture for better handling of sequential audio playback. This document explains the changes and how to use the test files.

## Architecture Changes

### Old System
- `play_tts_response()` returned a process handle dictionary
- Direct control over individual TTS processes
- Manual management of playback order

### New System
- `play_tts_response()` returns a boolean (success/failure)
- Queue-based system for sequential playback
- Automatic thread management for audio playback
- Global `current_playing_process` tracks the active audio

## Test Files

### 1. `test_tts.py` - Queue-based TTS Testing
Tests the new queue-based TTS system:
- Queuing TTS messages
- Checking playback status via global state
- Sequential playback of multiple messages
- Stopping the TTS player thread

**Usage:**
```bash
python tests/test_tts.py
```

### 2. `test_tts_direct.py` - Direct TTS Testing
Tests direct TTS playback (bypassing the queue):
- Uses `_play_tts_segment()` for immediate playback
- Direct process handle management
- Compatible with `is_playing()` and `stop_playing()`
- Useful for testing or special cases requiring direct control

**Usage:**
```bash
python tests/test_tts_direct.py
```

## API Changes

### Queue-based API (Recommended)
```python
from utils.tts import play_tts_response, stop_tts_player_thread

# Queue a TTS message
success = play_tts_response("Your text here")

# Stop all TTS playback and clear queue
stop_tts_player_thread()
```

### Direct API (Advanced Use)
```python
from utils.tts import _play_tts_segment, is_playing, stop_playing

# Play directly (bypasses queue)
process_handle = _play_tts_segment("Your text here")

# Check if playing
if is_playing(process_handle):
    # Stop playback
    stop_playing(process_handle)
```

## Migration Guide

If your code was using the old API:
```python
# Old code
process_handle = play_tts_response("Text")
if is_playing(process_handle):
    stop_playing(process_handle)
```

Update to either:

1. **Queue-based (Recommended):**
```python
# New code - queue-based
success = play_tts_response("Text")
# To stop all TTS:
stop_tts_player_thread()
```

2. **Direct playback (if needed):**
```python
# New code - direct
process_handle = _play_tts_segment("Text")
if is_playing(process_handle):
    stop_playing(process_handle)
```

## Benefits of the New System

1. **Sequential Playback**: Messages are automatically played in order
2. **Thread Safety**: Built-in thread management and locking
3. **Queue Management**: Can queue multiple messages without blocking
4. **Simplified API**: Just queue and forget for most use cases
5. **Backwards Compatibility**: Direct API still available for special cases
