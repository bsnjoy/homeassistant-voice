#!/usr/bin/env python3
import requests
import config
import os
from utils import audio

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
        # rarely homeassistan succeds to send the command, but connectiong hangs
        # to avoid user frustration, we terminate the connection after 5 seconds
        response = requests.post(url, headers=headers, json=data, timeout=5)
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
    required_attrs = ['action_aliases', 'device_aliases', 'room_entities', 'default_room']
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
    room_specified = False
    room = config.default_room
    for room_name, aliases in config.room_aliases.items():
        if any(alias in transcript for alias in aliases):
            room = room_name
            room_specified = True
            print(f"Room recognized: {room}")
            break
    
    # Check if this device can be used without specifying a room
    if not room_specified and hasattr(config, 'devices_without_room') and device in config.devices_without_room:
        # Search for the device across all rooms
        entity_id = None
        for search_room, devices in config.room_entities.items():
            if device in devices:
                entity_id = devices[device]
                room = search_room
                print(f"Found {device} in {room} without room specification")
                break
        
        if entity_id is None:
            print(f"No entity found for {device} in any room")
            return False
    else:
        # Get entity ID for the device in the specified room
        if room not in config.room_entities or device not in config.room_entities[room]:
            print(f"No entity found for {device} in {room}")
            return False
        
        entity_id = config.room_entities[room][device]
    
    print(f"Executing action: {action} on {entity_id} in {room}")
    
    # Send the command to Home Assistant
    success = send_homeassistant_command(entity_id, action)
    
    return success
