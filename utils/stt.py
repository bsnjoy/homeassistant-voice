import subprocess
import json
import requests
import config
import os
from utils.timing import time_execution

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
    
    endpoint = f"{config.whisper_url}/v1/audio/transcriptions"

    files = {
        "file": open(normalized_file, "rb")
    }

    try:
        response = requests.post(endpoint, files=files, data=config.whisper_config)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.text
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        files["file"].close()  # Make sure to close the file
