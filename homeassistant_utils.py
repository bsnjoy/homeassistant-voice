#!/usr/bin/env python3
import requests
import config

def send_homeassistant_command(entity_id, service):
    """
    Send a command to Home Assistant to control an entity.
    
    Args:
        entity_id (str): The entity ID to control
        action (str): The action to perform (turn_on, turn_off, etc.)
        
    Returns:
        bool: True if the command was successful, False otherwise
    """
    headers = {
        "Authorization": f"Bearer {config.homeassistant_token}",
        "Content-Type": "application/json",
    }
    
    # Determine the service to call based on the action
    domain = entity_id.split('.')[0]
    
    url = f"{config.homeassistant_url}/api/services/{domain}/{service}"
    
    data = {
        "entity_id": entity_id
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        print(f"Successfully sent command to Home Assistant: {service} {entity_id}")
        return True
    except Exception as e:
        print(f"Error sending command to Home Assistant: {e}")
        return False

def process_command(transcript):
    """
    Process the transcribed text to check if it matches any command or its aliases.
    If a match is found, execute the corresponding action.
    
    Args:
        transcript (str): The transcribed text to process
        
    Returns:
        bool: True if a command was matched and executed, False otherwise
    """
    if not transcript or not hasattr(config, 'commands'):
        return False
    
    # Convert transcript to lowercase for case-insensitive matching
    transcript = transcript.lower().strip()
    
    for cmd in config.commands:
        # Check if the command or any of its aliases appears in the transcript
        if cmd["command"] in transcript or any(alias in transcript for alias in cmd["aliases"]):
            print(f"Command recognized: {cmd['command']}")
            print(f"Executing action: {cmd['service']} on {cmd['entity_id']}")
            
            # Send the command to Home Assistant
            return send_homeassistant_command(cmd["entity_id"], cmd["service"])
    
    print(f"No matching command found for: '{transcript}'")
    return False
