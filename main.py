#!/usr/bin/env python3
import sys
import time
import os
import datetime
import numpy as np
from threading import Thread
from queue import Queue, Empty
import config
import audio_utils
import homeassistant_utils

def process_audio_and_detect_speech():
    """
    Process audio stream, detect speech, and transcribe when appropriate.
    Returns when a complete transcription cycle is done or no speech is detected.
    """
    process = audio_utils.get_audio_stream()
    
    # Initialize variables
    is_recording = False
    silence_start_time = None
    recorded_audio = bytearray()
    audio_buffer = bytearray()
    chunk_size = int(config.SAMPLE_RATE * 0.1)  # 100ms chunks
    
    try:
        while True:
            # Read chunk of audio data
            audio_data = process.stdout.read(chunk_size * config.SAMPLE_WIDTH)
            if len(audio_data) == 0:
                break
                
            # Add to buffer
            audio_buffer.extend(audio_data)
            
            # Convert to numpy array for analysis
            samples = np.frombuffer(audio_data, dtype=np.int16)
            
            # Calculate RMS and dB
            rms = audio_utils.rms_from_samples(samples)
            db = audio_utils.db_from_rms(rms)
            
            # Display current volume level
            audio_utils.display_volume(db, is_recording)
            
            # Check if we're above the threshold
            if db >= config.DB_THRESHOLD:
                if not is_recording:
                    print("\nSpeech detected, recording...")
                    is_recording = True
                    # Start with some pre-roll from the buffer
                    preroll_size = min(len(audio_buffer), int(config.SAMPLE_RATE * config.PREROLL_DURATION_SEC) * config.SAMPLE_WIDTH)
                    recorded_audio = bytearray(audio_buffer[-preroll_size:])
                
                # Reset silence timer
                silence_start_time = None
                
                # Add the current chunk to our recording
                recorded_audio.extend(audio_data)
            
            # If we're recording and below threshold, check for silence duration
            elif is_recording:
                recorded_audio.extend(audio_data)
                
                if silence_start_time is None:
                    silence_start_time = time.time()
                elif (time.time() - silence_start_time) * 1000 >= config.SILENCE_THRESHOLD_MS:
                    # Silence duration exceeded threshold, stop recording
                    recording_length_sec = len(recorded_audio) / (config.SAMPLE_RATE * config.SAMPLE_WIDTH)
                    
                    print(f"\nSilence detected, recording length: {recording_length_sec:.2f} seconds")
                    
                    if recording_length_sec >= config.MIN_RECORDING_LENGTH_SEC:
                        # Save the recording with auto-generated filename
                        saved_path = audio_utils.save_audio_to_file(recorded_audio)
                        print(f"Saved recording to {saved_path}")
                        
                        # Send to server for transcription
                        print("Transcribing...")
                        transcript = audio_utils.send_to_whisper(saved_path)
                        print(f"\nTranscription: {transcript}")
                        
                        # Clean up and return the transcript
                        process.terminate()
                        return transcript
                    else:
                        print("Recording too short, discarding")
                    
                    # Reset recording state
                    is_recording = False
                    recorded_audio = bytearray()
                    silence_start_time = None
            
            # Keep buffer at a reasonable size (last 1 second)
            max_buffer_size = config.SAMPLE_RATE * config.SAMPLE_WIDTH
            if len(audio_buffer) > max_buffer_size:
                audio_buffer = audio_buffer[-max_buffer_size:]
                
    except KeyboardInterrupt:
        pass
    finally:
        process.terminate()
    
    return None


def main():
    """Main function to run the speech detection and transcription system."""
    print(f"Speech Detection and Transcription System")
    print(f"Speech threshold: {config.DB_THRESHOLD} dB, Silence threshold: {config.SILENCE_THRESHOLD_MS} ms")
    print(f"Loaded {len(config.commands) if hasattr(config, 'commands') else 0} commands")
    print("Press Ctrl+C to exit")
    
    try:
        while True:
            transcript = process_audio_and_detect_speech()
            if transcript:
                homeassistant_utils.process_command(transcript)
            # Give a small pause between detection cycles
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nExiting")
        sys.exit(0)

if __name__ == "__main__":
    main()
