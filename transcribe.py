#!/usr/bin/env python3
import sys
import os
import audio_utils
import config

def main():
    """
    Test script for transcribing audio files using the Whisper API.
    
    Usage:
        python transcribe.py <audio_file_path>
    
    Example:
        python transcribe.py recordings/2025/02/27/recording_20250227_101030.wav
    """
    # Check if a file path was provided
    if len(sys.argv) < 2:
        print("Error: Please provide the path to an audio file.")
        print(f"Usage: python {sys.argv[0]} <audio_file_path>")
        sys.exit(1)
    
    # Get the file path from command line arguments
    audio_file = sys.argv[1]
    
    # Check if the file exists
    if not os.path.exists(audio_file):
        print(f"Error: File not found: {audio_file}")
        sys.exit(1)
    
    print(f"Transcribing file: {audio_file}")
    print(f"Using Whisper API at: {config.server_url}")
    print(f"Model: {config.model}")
    print(f"Response format: {config.response_format}")
    
    # Send the file to Whisper for transcription
    print("Sending to Whisper API...")
    transcript = audio_utils.send_to_whisper(audio_file)
    
    # Display the result
    if transcript:
        print("\nTranscription result:")
        print("-" * 40)
        print(transcript)
        print("-" * 40)        
    else:
        print("Transcription failed.")

if __name__ == "__main__":
    main()
