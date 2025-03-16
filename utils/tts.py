#!/usr/bin/env python3
import subprocess
import json
import config
from utils.russian_number_converter import convert_numbers_to_russian_words
from utils.timing import time_execution

@time_execution(label="Starting TTS request")
def play_tts_response(text):
    """
    Convert text to speech using the TTS API and play it.
    
    Args:
        text (str): The text to convert to speech
        
    Returns:
        dict: A dictionary containing the processes or None if failed
    """
    try:
        optimized_text = convert_numbers_to_russian_words(text)

        # Prepare the JSON data for the TTS API
        json_data = json.dumps({"text": optimized_text, "format": "wav", "streaming": "True", "seed": 1})
        
        # Construct the curl command
        curl_cmd = [
            'curl',
            '-X', 'POST',
            config.TTS_API_URL,
            '-H', 'Content-Type: application/json',
            '-d', json_data,
            '--output', '-'
        ]
        
        # Get the audio play command from config
        audio_play_cmd = config.AUDIO_PLAY_CMD
        
        # Start the curl process
        curl_process = subprocess.Popen(
            curl_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Start the audio play process, using the output from curl as input
        play_process = subprocess.Popen(
            audio_play_cmd,
            stdin=curl_process.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )
        
        # Allow curl_process to receive a SIGPIPE if play_process exits
        curl_process.stdout.close()
        
        # Return the processes without waiting
        return {
            "curl_process": curl_process,
            "play_process": play_process
        }
    except Exception as e:
        print(f"Error starting TTS response: {e}")
        return None

def is_playing(process_handle):
    """
    Check if the TTS audio is still playing.
    
    Args:
        process_handle (dict): The process handle returned by play_tts_response
        
    Returns:
        bool: True if still playing, False otherwise
    """
    if not process_handle:
        return False
    
    curl_process = process_handle.get("curl_process")
    play_process = process_handle.get("play_process")
    
    # Check if both processes are still running
    if curl_process and play_process:
        return curl_process.poll() is None or play_process.poll() is None
    
    return False

def stop_playing(process_handle):
    """
    Stop the TTS audio playback.
    
    Args:
        process_handle (dict): The process handle returned by play_tts_response
        
    Returns:
        bool: True if successfully stopped, False otherwise
    """
    if not process_handle:
        return False
    
    try:
        curl_process = process_handle.get("curl_process")
        play_process = process_handle.get("play_process")
        
        # Terminate both processes if they're still running
        if curl_process and curl_process.poll() is None:
            curl_process.terminate()
        
        if play_process and play_process.poll() is None:
            play_process.terminate()
        
        return True
    except Exception as e:
        print(f"Error stopping TTS playback: {e}")
        return False
