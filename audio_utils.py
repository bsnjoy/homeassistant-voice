#!/usr/bin/env python3
import subprocess
import numpy as np
import wave
import os
import requests
import config

# Audio configuration is in config.py

def get_audio_stream():
    """Start the audio capture process using arecord and return the process."""
    cmd = ["arecord", "-D", "dsnoop:CARD=MS,DEV=0", "-r", str(config.SAMPLE_RATE), "-c", str(config.CHANNELS), 
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
        wf.setnchannels(config.CHANNELS)
        wf.setsampwidth(config.SAMPLE_WIDTH)
        wf.setframerate(config.SAMPLE_RATE)
        wf.writeframes(audio_data)
    return filename

def display_volume(db, is_recording):
    """
    Display current volume level with a visual meter.
    
    Parameters:
    - db (float): The current decibel level
    - is_recording (bool): Whether currently recording or just listening
    
    Returns:
    - None (prints to console)
    """
    width = 40
    normalized_db = max(0, min(1, (db - 30) / 40)) if db > -100 else 0
    num_bars = int(normalized_db * width)
    meter = "│" + "█" * num_bars + " " * (width - num_bars) + "│"
    status = "RECORDING" if is_recording else "LISTENING"
    print(f"\r{status}: {meter} {db:.1f} dB", end="")

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
