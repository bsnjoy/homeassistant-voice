#!/usr/bin/env python3
import requests
import config
import openai
from utils import tts
from datetime import datetime
from utils.timing import time_execution

def is_ai_command(text):
    """
    Check if the text is a command meant for the AI assistant.
    
    Args:
        text (str): The text to check
        
    Returns:
        bool: True if the text is a command for the AI assistant, False otherwise
    """
    for name in config.ai_assistant_names:
        if text.lower().startswith(name.lower()):
            return True
    return False

def send_to_openai(text):
    """
    Send text to OpenAI GPT-4o to get a response.
    
    Args:
        text (str): The text to send to OpenAI
        
    Returns:
        str: The response from OpenAI, or None if an error occurred
    """
    try:
        # Configure the OpenAI client with the API key
        client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        
        # Create the chat completion
        response = client.chat.completions.create(
            model="gpt-4o",  # Using GPT-4o
            messages=[
                {"role": "system", "content": f"You are Алиса, an AI assistant and a smart speaker (колонка). The current date and time is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"},
                {"role": "user", "content": text}
            ]
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error sending request to OpenAI: {e}")
        return None

@time_execution(label="API request to OpenAI and TTS")
def process_ai_command(text):
    """
    Process a command meant for the AI assistant.
    
    Args:
        text (str): The text to process
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Remove the AI assistant name from the beginning of the text
    for name in config.ai_assistant_names:
        if text.lower().startswith(name.lower()):
            # Remove the name and any leading/trailing whitespace
            text = text[len(name):].strip()
            break
    
    # Send the text to OpenAI to get a response
    response = send_to_openai(text)
    if not response:
        print("Failed to get response from OpenAI")
        return False
    
    # Play the response using TTS
    success = tts.play_tts_response(response)
    return success
