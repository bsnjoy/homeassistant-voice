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
    Process the transcribed text to check if it matches action, device, and room aliases.
    If matches are found, execute the corresponding action on the device in the specified room.
    
    Args:
        transcript (str): The transcribed text to process
        
    Returns:
        bool: True if a command was matched and executed, False otherwise
    """
    if not transcript:
        return False
    
    # Check if we have the necessary configuration
    required_attrs = ['action_aliases', 'device_aliases', 'device_entities', 'default_room']
    if not all(hasattr(config, attr) for attr in required_attrs):
        print("Missing required configuration attributes")
        return False
    
    # Convert transcript to lowercase for case-insensitive matching
    transcript = transcript.lower().strip()
    
    # Find action in transcript
    action = None
    for action_name, aliases in config.action_aliases.items():
        if any(alias in transcript for alias in aliases):
            action = action_name
            print(f"Action recognized: {action}")
            break
    
    if not action:
        print("No action recognized in transcript")
        return False
    
    # Find device in transcript
    device = None
    for device_name, aliases in config.device_aliases.items():
        if any(alias in transcript for alias in aliases):
            device = device_name
            print(f"Device recognized: {device}")
            break
    
    if not device:
        print("No device recognized in transcript")
        return False
    
    # Find room in transcript (optional)
    room = config.default_room
    for room_name, aliases in config.room_aliases.items():
        if any(alias in transcript for alias in aliases):
            room = room_name
            print(f"Room recognized: {room}")
            break
    
    # Get entity ID for the device in the specified room
    if device not in config.device_entities or room not in config.device_entities[device]:
        print(f"No entity found for {device} in {room}")
        return False
    
    entity_id = config.device_entities[device][room]
    print(f"Executing action: {action} on {entity_id}")
    
    # Send the command to Home Assistant
    return send_homeassistant_command(entity_id, action)
