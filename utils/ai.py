#!/usr/bin/env python3
import requests
import config
from utils import tts

def send_to_openai(text):
    """
    Send text to OpenAI to get a response.
    
    Args:
        text (str): The text to send to OpenAI
        
    Returns:
        str: The response from OpenAI, or None if an error occurred
    """
    # This is a placeholder for the actual OpenAI API call
    # You'll need to replace this with the actual API call to OpenAI
    try:
        # Example OpenAI API call (replace with actual implementation)
        # response = requests.post(
        #     "https://api.openai.com/v1/chat/completions",
        #     headers={
        #         "Authorization": f"Bearer {config.openai_api_key}",
        #         "Content-Type": "application/json"
        #     },
        #     json={
        #         "model": "gpt-3.5-turbo",
        #         "messages": [{"role": "user", "content": text}]
        #     }
        # )
        # response.raise_for_status()
        # return response.json()["choices"][0]["message"]["content"]
        
        # For now, return a simple response for testing
        return f"You said: {text}"
    except Exception as e:
        print(f"Error sending request to OpenAI: {e}")
        return None

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
