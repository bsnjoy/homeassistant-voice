#!/usr/bin/env python3
import subprocess
import json
import config

def play_tts_response(text):
    """
    Convert text to speech using the TTS API and play it.
    
    Args:
        text (str): The text to convert to speech
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Prepare the JSON data for the TTS API
        json_data = json.dumps({"text": text, "format": "wav", "streaming": "True", "seed": 1})
        
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
        
        # Wait for both processes to complete
        play_process.wait()
        curl_process.wait()
        
        if curl_process.returncode != 0:
            stderr = curl_process.stderr.read().decode()
            print(f"Error in TTS API request: {stderr}")
            return False
        
        if play_process.returncode != 0:
            stderr = play_process.stderr.read().decode()
            print(f"Error playing audio: {stderr}")
            return False
        
        return True
    except Exception as e:
        print(f"Error playing TTS response: {e}")
        return False
