#!/usr/bin/env python3
import subprocess
import numpy as np
import sys
import time
import os
import wave
import json
import socket
import struct
import datetime
from threading import Thread
from queue import Queue, Empty
import requests
import config

# Configuration
SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2  # 16-bit audio (S16_LE)
CHANNELS = 1

# Ensure recordings directory exists
os.makedirs(config.RECORDINGS_DIR, exist_ok=True)

def get_audio_stream():
    """Start the audio capture process using arecord and return the process."""
    cmd = ["arecord", "-D", "dsnoop:CARD=MS,DEV=0", "-r", str(SAMPLE_RATE), "-c", str(CHANNELS), 
           "-f", "S16_LE", "-t", "raw"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return process

def db_from_rms(rms):
    """Convert RMS value to decibels."""
    if rms <= 0:
        return -100  # A very low dB value for silence
    return 20 * np.log10(rms)

def rms_from_samples(samples):
    """Calculate RMS from audio samples."""
    return np.sqrt(np.mean(samples.astype(np.float32)**2))

def save_audio_to_file(audio_data, filename):
    """Save audio data to a WAV file."""
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_data)
    return filename



def send_to_whisper(audio_file):
    """
    Send an audio file to Whisper API for transcription.

    Parameters:
    - audio_file (str): Path to the audio file

    Returns:
    - The transcription result if successful
    - None if an error occurred
    """
    endpoint = f"{config.server_url}/v1/audio/transcriptions"

    files = {
        "file": open(audio_file, "rb")
    }

    data = {
        "model": config.model,
        "response_format": config.response_format
    }

    try:
        response = requests.post(endpoint, files=files, data=data)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.text
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        files["file"].close()  # Make sure to close the file

def process_audio_and_detect_speech():
    """
    Process audio stream, detect speech, and transcribe when appropriate.
    Returns when a complete transcription cycle is done or no speech is detected.
    """
    process = get_audio_stream()
    
    # Initialize variables
    is_recording = False
    silence_start_time = None
    recorded_audio = bytearray()
    audio_buffer = bytearray()
    chunk_size = int(SAMPLE_RATE * 0.1)  # 100ms chunks
    
    try:
        while True:
            # Read chunk of audio data
            audio_data = process.stdout.read(chunk_size * SAMPLE_WIDTH)
            if len(audio_data) == 0:
                break
                
            # Add to buffer
            audio_buffer.extend(audio_data)
            
            # Convert to numpy array for analysis
            samples = np.frombuffer(audio_data, dtype=np.int16)
            
            # Calculate RMS and dB
            rms = rms_from_samples(samples)
            db = db_from_rms(rms)
            
            # Display current volume level
            width = 40
            normalized_db = max(0, min(1, (db - 30) / 40)) if db > -100 else 0
            num_bars = int(normalized_db * width)
            meter = "│" + "█" * num_bars + " " * (width - num_bars) + "│"
            status = "RECORDING" if is_recording else "LISTENING"
            print(f"\r{status}: {meter} {db:.1f} dB", end="")
            
            # Check if we're above the threshold
            if db >= config.DB_THRESHOLD:
                if not is_recording:
                    print("\nSpeech detected, recording...")
                    is_recording = True
                    # Start with some pre-roll from the buffer (last 200ms)
                    preroll_size = min(len(audio_buffer), int(SAMPLE_RATE * 0.2) * SAMPLE_WIDTH)
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
                    recording_length_sec = len(recorded_audio) / (SAMPLE_RATE * SAMPLE_WIDTH)
                    
                    print(f"\nSilence detected, recording length: {recording_length_sec:.2f} seconds")
                    
                    if recording_length_sec >= config.MIN_RECORDING_LENGTH_SEC:
                        # Generate filename with timestamp
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = os.path.join(config.RECORDINGS_DIR, f"recording_{timestamp}.wav")
                        
                        # Save the recording
                        save_audio_to_file(recorded_audio, filename)
                        print(f"Saved recording to {filename}")
                        
                        # Send to server for transcription
                        print("Transcribing...")
                        transcript = send_to_whisper(filename)
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
            max_buffer_size = SAMPLE_RATE * SAMPLE_WIDTH
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
    print("Press Ctrl+C to exit")
    
    try:
        while True:
            transcript = process_audio_and_detect_speech()
            # Give a small pause between detection cycles
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nExiting")
        sys.exit(0)

if __name__ == "__main__":
    main()
