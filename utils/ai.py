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

@time_execution(label="API request to OpenAI")
def send_to_openai_streaming(text):
    """
    Send text to OpenAI GPT-4o using streaming mode and process chunks as they arrive.
    
    Args:
        text (str): The text to send to OpenAI
        
    Returns:
        generator: A generator that yields text chunks as they are received
    """
    try:
        # Configure the OpenAI client with the API key
        client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        
        # Create the chat completion with streaming enabled
        stream = client.chat.completions.create(
            model="gpt-4o",  # Using GPT-4o
            messages=[
                {"role": "system", "content": f"You are Алиса, an AI assistant and a smart speaker (колонка). The current date and time is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. All dates and numbers should be printed in text to read."},
                {"role": "user", "content": text}
            ],
            stream=True  # Enable streaming
        )
        
        # Return the stream for processing by the caller
        return stream
    except Exception as e:
        print(f"Error sending streaming request to OpenAI: {e}")
        return None

def process_ai_command(text):
    """
    Process a command meant for the AI assistant using streaming.
    
    Args:
        text (str): The text to process
        
    Returns:
        None: This function now handles the streaming and TTS directly
    """
    # Remove the AI assistant name from the beginning of the text
    for name in config.ai_assistant_names:
        if text.lower().startswith(name.lower()):
            # Remove the name and any leading/trailing whitespace
            text = text[len(name):].strip()
            break
    
    # Send the text to OpenAI to get a streaming response
    stream = send_to_openai_streaming(text)
    if not stream:
        print("Failed to get streaming response from OpenAI")
        return None
    
    # Process the streaming response
    process_streaming_response(stream)
    return None

def process_streaming_response(stream):
    """
    Process the streaming response from OpenAI, splitting by punctuation
    and sending to TTS as soon as complete segments are available.
    
    Args:
        stream: The streaming response from OpenAI
    """
    if not stream:
        return
    
    buffer = ""
    full_response = ""
    segments_to_play = []
    current_segment = ""
    
    # Process each chunk as it arrives
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            # Get the content from this chunk
            content = chunk.choices[0].delta.content
            buffer += content
            full_response += content
            
            # Check if we have a complete segment (ending with . or ,)
            if '.' in buffer or ',' in buffer:
                # Split by periods and commas
                parts = []
                temp = buffer
                
                # First split by periods
                period_parts = temp.split('.')
                for i, part in enumerate(period_parts):
                    if i < len(period_parts) - 1:
                        # This part ends with a period
                        parts.append(part + '.')
                    else:
                        # Last part might not end with a period
                        # Split it further by commas
                        comma_parts = part.split(',')
                        for j, comma_part in enumerate(comma_parts):
                            if j < len(comma_parts) - 1:
                                # This part ends with a comma
                                parts.append(comma_part + ',')
                            else:
                                # Last part, might not end with anything
                                if comma_part.strip():
                                    parts.append(comma_part)
                
                # Add complete parts to segments to play
                for i in range(len(parts) - 1):
                    segments_to_play.append(parts[i])
                
                # Keep the last part in the buffer
                buffer = parts[-1] if parts else ""
                
                # Send complete segments to TTS
                if segments_to_play:
                    for segment in segments_to_play:
                        print(f"Sending segment to TTS: {segment}")
                        tts.play_tts_response(segment)
                    segments_to_play = []
    
    # Process any remaining text in the buffer
    if buffer.strip():
        print(f"Sending final segment to TTS: {buffer}")
        tts.play_tts_response(buffer)
    
    print(f"Full OpenAI response: {full_response}")
