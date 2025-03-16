#!/usr/bin/env python3
import subprocess
import numpy as np
import wave
import os
import requests
import datetime
import time
import config
from utils.timing import time_execution

# Audio configuration is in config.py

def get_audio_stream():
    """Start the audio capture process and return the process."""
    process = subprocess.Popen(config.AUDIO_RECORD_CMD, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return process

def db_from_rms(rms):
    """Convert RMS value to decibels."""
    if rms <= 0:
        return -100  # A very low dB value for silence
    return 20 * np.log10(rms)

def rms_from_samples(samples):
    """Calculate RMS from audio samples."""
    return np.sqrt(np.mean(samples.astype(np.float32)**2))

def save_audio_to_file(audio_data, filename=None):
    """
    Save audio data to a WAV file, organizing files in a year-month-date directory structure.
    
    Parameters:
    - audio_data (bytes): The audio data to save
    - filename (str, optional): The filename or path to save to. If None, a filename will be generated
                               with the current timestamp.
    
    Returns:
    - str: The full path to the saved file
    """
    now = datetime.datetime.now()
    
    # If no filename is provided, generate one with timestamp
    if filename is None:
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}.wav"
    
    # Check if the filename is a full path or just a basename
    if os.path.dirname(filename):
        # It's a full path, use it as is
        final_path = filename
    else:
        # It's just a basename, organize it in YYYY/MM/DD subdirectories
        year_dir = now.strftime("%Y")
        month_dir = now.strftime("%m")
        day_dir = now.strftime("%d")
        
        # Create the directory structure
        recording_path = os.path.join(config.RECORDINGS_DIR, year_dir, month_dir, day_dir)
        os.makedirs(recording_path, exist_ok=True)
        
        # Create the full path
        final_path = os.path.join(recording_path, filename)
    
    # Save the audio data
    with wave.open(final_path, 'wb') as wf:
        wf.setnchannels(config.CHANNELS)
        wf.setsampwidth(config.SAMPLE_WIDTH)
        wf.setframerate(config.SAMPLE_RATE)
        wf.writeframes(audio_data)
    
    return final_path

def display_volume(db, is_recording):
    """
    Display current volume level with a visual meter.
    
    Parameters:
    - db (float): The current decibel level
    - is_recording (bool): Whether currently recording or just listening
    
    Returns:
    - None (prints to console)
    """
    # Static variable to track previous state
    if not hasattr(display_volume, "prev_recording"):
        display_volume.prev_recording = False
    
    width = 40
    normalized_db = max(0, min(1, (db - 30) / 40)) if db > -100 else 0
    num_bars = int(normalized_db * width)
    meter = "│" + "█" * num_bars + " " * (width - num_bars) + "│"
    status = "RECORDING" if is_recording else "LISTENING"
    
    # Add a newline when transitioning from recording to listening
    if display_volume.prev_recording and not is_recording:
        print()  # Print a newline
    
    print(f"\r{status}: {meter} {db:.1f} dB", end="")
    
    # Update previous state
    display_volume.prev_recording = is_recording

@time_execution(label="Playing audio that job is finished")
def play_audio(audio_file):
    """
    Play an audio file using the system's audio player in the background.
    
    Parameters:
    - audio_file (str): Path to the audio file to play
    
    Returns:
    - subprocess.Popen: The process object if successful, None otherwise
    """
    # Check if file exists
    if not os.path.isfile(audio_file):
        print(f"Not playing audio: File does not exist: {audio_file}")
        return None
        
    try:
        # Use the audio play command from config
        cmd = config.AUDIO_PLAY_CMD + [audio_file]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        # Return the process without waiting
        return process
    except Exception as e:
        print(f"Error playing audio: {e}")
        return None

@time_execution(label="Normalizing audio")
def normalize_audio(input_file):
    """
    Normalize audio using sox to improve transcription quality.
    
    Parameters:
    - input_file (str): Path to the input audio file
    
    Returns:
    - str: Path to the normalized audio file
    """
    # Create output filename by adding _normalized before the extension
    base, ext = os.path.splitext(input_file)
    output_file = f"{base}_normalized{ext}"
    
    # Create the sox command with the actual input and output files
    normalize_cmd = config.AUDIO_NORMALIZE_CMD.copy()
    for i, item in enumerate(normalize_cmd):
        if item == "INPUT_FILE":
            normalize_cmd[i] = input_file
        elif item == "OUTPUT_FILE":
            normalize_cmd[i] = output_file
    
    try:
        # Execute the normalization command
        subprocess.run(normalize_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Error normalizing audio: {e}")
        return input_file  # Return original file if normalization fails
    except Exception as e:
        print(f"Unexpected error during audio normalization: {e}")
        return input_file  # Return original file if normalization fails

@time_execution(label="Transcribing audio")
def send_to_whisper(audio_file):
    """
    Send an audio file to Whisper API for transcription.
    Normalizes the audio before sending for better transcription quality.

    Parameters:
    - audio_file (str): Path to the audio file

    Returns:
    - The transcription result if successful
    - None if an error occurred
    """
    # Note: Normalization is now handled in main.py for timing purposes
    normalized_file = audio_file
    if not normalized_file.endswith("_normalized.wav"):
        normalized_file = normalize_audio(audio_file)
    
    endpoint = f"{config.server_url}/v1/audio/transcriptions"

    files = {
        "file": open(normalized_file, "rb")
    }


    try:
        response = requests.post(endpoint, files=files, data=config.Whisper)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.text
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        files["file"].close()  # Make sure to close the file
