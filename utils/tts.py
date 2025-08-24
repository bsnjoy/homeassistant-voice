#!/usr/bin/env python3
import subprocess
import json
import config
from utils.russian_number_converter import convert_numbers_to_russian_words
from utils.timing import time_execution

# Queue to store TTS segments for sequential playback
import queue
import threading
import time

# Create a queue for TTS segments
tts_queue = queue.Queue()
# Flag to indicate if the TTS player thread is running
tts_player_running = False
# Lock for thread safety
tts_lock = threading.Lock()
# Current playing process handle
current_playing_process = None

def start_tts_player_thread():
    """
    Start a thread to play TTS segments from the queue in order.
    """
    global tts_player_running
    
    with tts_lock:
        if tts_player_running:
            return
        tts_player_running = True
    
    # Start the player thread
    tts_thread = threading.Thread(target=tts_player_worker, daemon=True)
    tts_thread.start()
    print("TTS player thread started")

def tts_player_worker():
    """
    Worker function for the TTS player thread.
    Plays TTS segments from the queue in order.
    """
    global tts_player_running, current_playing_process
    
    try:
        while True:
            # Get the next segment from the queue (blocks until an item is available)
            segment = tts_queue.get()
            
            if segment is None:
                # None is used as a signal to stop the thread
                break
            
            # Play the segment
            process_handle = _play_tts_segment(segment)
            
            # Store the current playing process
            with tts_lock:
                current_playing_process = process_handle
            
            # Wait for the segment to finish playing
            if process_handle:
                while is_playing(process_handle):
                    time.sleep(0.1)
            
            # Clear the current playing process
            with tts_lock:
                current_playing_process = None
            
            # Mark the task as done
            tts_queue.task_done()
    except Exception as e:
        print(f"Error in TTS player thread: {e}")
    finally:
        with tts_lock:
            tts_player_running = False
            current_playing_process = None

@time_execution(label="Starting TTS request")
def play_tts_response(text):
    """
    Convert text to speech using the TTS API and queue it for playback.
    
    Args:
        text (str): The text to convert to speech
        
    Returns:
        bool: True if the text was successfully queued, False otherwise
    """
    try:
        # Make sure the player thread is running
        start_tts_player_thread()
        
        # Add the text to the queue
        tts_queue.put(text)
        return True
    except Exception as e:
        print(f"Error queueing TTS response: {e}")
        return False

def _play_tts_segment(text):
    """
    Internal function to convert text to speech using the TTS API and play it.
    
    Args:
        text (str): The text to convert to speech
        
    Returns:
        dict: A dictionary containing the processes or None if failed
    """
    try:
        optimized_text = convert_numbers_to_russian_words(text)
        # remove sybols: * , . from the text to avoid issues with the TTS API
        optimized_text = optimized_text.replace('*', '').replace(',', '').replace('.', '')

        # Prepare the JSON data for the new TTS API
        json_data = json.dumps({"text": optimized_text})
        
        # Construct the curl command for the new API to output to stdout
        curl_cmd = [
            'curl',
            '-X', 'POST',
            '-H', 'Content-Type: application/json',
            '-d', json_data,
            '--output', '-',  # Output to stdout
            config.TTS_API_URL
        ]
        
        # Get the audio play command from config
        audio_play_cmd = config.VOICE_PLAY_CMD.copy()
        
        # For sox, we need to specify the input format as WAV when reading from stdin
        if audio_play_cmd[0] == 'sox':
            # Modify the command to read WAV from stdin
            audio_play_cmd = ['sox', '-t', 'wav', '-', '-d']
        
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
    
    # Check if either process is still running
    if curl_process and play_process:
        return curl_process.poll() is None or play_process.poll() is None
    elif play_process:
        return play_process.poll() is None
    
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

def stop_tts_player_thread():
    """
    Stop the TTS player thread and clear any pending TTS segments.
    
    Returns:
        bool: True if successfully stopped, False otherwise
    """
    global tts_player_running, current_playing_process
    
    try:
        with tts_lock:
            if not tts_player_running:
                return True
            
            # Stop any currently playing audio
            if current_playing_process:
                stop_playing(current_playing_process)
                current_playing_process = None
        
        # Clear the queue of any pending segments
        while not tts_queue.empty():
            try:
                tts_queue.get_nowait()
                tts_queue.task_done()
            except queue.Empty:
                break
        
        # Signal the thread to stop by adding None to the queue
        tts_queue.put(None)
        
        # Give the thread a moment to exit gracefully
        time.sleep(0.1)
        
        return True
    except Exception as e:
        print(f"Error stopping TTS player thread: {e}")
        return False
