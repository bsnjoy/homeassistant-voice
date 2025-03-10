#!/usr/bin/env python3
import sys
import time
import os
import datetime
import numpy as np
import signal
from threading import Thread, Event, Lock
from collections import deque
import config
import audio_utils
import homeassistant_utils

# Force stdout and stderr to be unbuffered to ensure logs appear immediately in systemd journal
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Define a logging function that ensures output is flushed immediately
def log_message(message):
    """Log a message to stdout and ensure it's flushed immediately."""
    print(message, flush=True)

class AudioCaptureThread(Thread):
    """Thread class for capturing audio continuously in the background using a ring buffer."""
    
    def __init__(self, buffer_duration=10.0, chunk_duration=0.05):
        """
        Initialize the audio capture thread with a ring buffer.
        
        Parameters:
        - buffer_duration: Total duration of the ring buffer in seconds
        - chunk_duration: Duration of each audio chunk in seconds
        """
        Thread.__init__(self, daemon=True)
        self.chunk_size = int(config.SAMPLE_RATE * chunk_duration) * config.SAMPLE_WIDTH
        self.buffer_size = int(buffer_duration / chunk_duration)  # Number of chunks to store
        
        # Ring buffer to store audio data with timestamps
        self.buffer = deque(maxlen=self.buffer_size)
        self.buffer_lock = Lock()  # Lock for thread-safe buffer access
        
        # Event to signal thread to stop
        self.stop_event = Event()
        self.process = None
        
        # For volume level display
        self.current_db = -100
        self.is_recording = False
    
    def run(self):
        """Main method to run the thread."""
        self.process = audio_utils.get_audio_stream()
        
        try:
            while not self.stop_event.is_set():
                # Read chunk of audio data
                audio_data = self.process.stdout.read(self.chunk_size)
                if len(audio_data) == 0:
                    break
                
                # Get current timestamp
                current_time = time.time()
                
                # Calculate audio metrics for monitoring
                samples = np.frombuffer(audio_data, dtype=np.int16)
                rms = audio_utils.rms_from_samples(samples)
                db = audio_utils.db_from_rms(rms)
                self.current_db = db
                
                # Add to ring buffer with timestamp
                with self.buffer_lock:
                    self.buffer.append((current_time, audio_data, db))
                
                # Small sleep to prevent CPU hogging
                time.sleep(0.001)
                
        except Exception as e:
            log_message(f"Error in audio capture thread: {e}")
        finally:
            if self.process:
                self.process.terminate()
    
    def get_audio_segment(self, start_time, end_time=None):
        """
        Extract audio segment from the ring buffer based on timestamps.
        
        Parameters:
        - start_time: Start timestamp for the segment
        - end_time: End timestamp for the segment (defaults to current time)
        
        Returns:
        - bytearray containing the audio segment
        """
        if end_time is None:
            end_time = time.time()
        
        segment = bytearray()
        
        with self.buffer_lock:
            # Make a copy to avoid modifying during iteration
            buffer_copy = list(self.buffer)
        
        # Extract chunks that fall within the time range
        for timestamp, data, _ in buffer_copy:
            if start_time <= timestamp <= end_time:
                segment.extend(data)
        
        return segment
    
    def get_current_db(self):
        """Get the current decibel level."""
        return self.current_db
    
    def set_recording_state(self, is_recording):
        """Set the recording state for display purposes."""
        self.is_recording = is_recording
    
    def get_recording_state(self):
        """Get the current recording state."""
        return self.is_recording
    
    def stop(self):
        """Signal the thread to stop."""
        self.stop_event.set()
        if self.process:
            self.process.terminate()


def process_audio_and_detect_speech(capture_thread, show_volume=True):
    """
    Process audio from the capture thread, detect speech, and transcribe when appropriate.
    Returns when a complete transcription cycle is done or no speech is detected.
    
    Parameters:
    - capture_thread: The AudioCaptureThread instance
    - show_volume: Whether to display the volume meter
    
    Returns:
    - transcript: The transcribed text if successful, None otherwise
    """
    # Initialize variables
    is_recording = False
    silence_start_time = None
    speech_start_time = None
    preroll_duration = config.PREROLL_DURATION_SEC
    
    # For display updates
    last_display_time = time.time()
    display_interval = 0.1  # Update display every 100ms
    
    try:
        while True:
            # Get current dB level from capture thread
            current_db = capture_thread.get_current_db()
            
            # Update display at regular intervals if enabled
            current_time = time.time()
            if show_volume and current_time - last_display_time >= display_interval:
                audio_utils.display_volume(current_db, is_recording)
                last_display_time = current_time
            
            # Check if we're above the threshold
            if current_db >= config.DB_THRESHOLD:
                if not is_recording:
                    log_message("\nSpeech detected, recording...")
                    is_recording = True
                    capture_thread.set_recording_state(True)
                    
                    # Set speech start time with preroll
                    speech_start_time = current_time - preroll_duration
                
                # Reset silence timer
                silence_start_time = None
            
            # If we're recording and below threshold, check for silence duration
            elif is_recording:
                if silence_start_time is None:
                    silence_start_time = current_time
                elif (current_time - silence_start_time) * 1000 >= config.SILENCE_THRESHOLD_MS:
                    # Silence duration exceeded threshold, stop recording
                    
                    # Extract the complete audio segment from the buffer
                    recorded_audio = capture_thread.get_audio_segment(speech_start_time, current_time)
                    recording_length_sec = len(recorded_audio) / (config.SAMPLE_RATE * config.SAMPLE_WIDTH)
                    
                    silence_end_time = time.time()
                    silence_detection_time = (silence_end_time - silence_start_time) * 1000
                    log_message(f"\nSilence detected, recording length: {recording_length_sec:.2f} seconds")
                    log_message(f"1. Period after speech ended (silence detection): {silence_detection_time:.2f} ms")
                    
                    if recording_length_sec >= config.MIN_RECORDING_LENGTH_SEC:
                        # Save the recording with auto-generated filename
                        saved_path = audio_utils.save_audio_to_file(recorded_audio)
                        log_message(f"Saved recording to {saved_path}")
                        
                        # Send to server for transcription
                        log_message("Transcribing...")
                        normalize_start_time = time.time()
                        normalized_file = audio_utils.normalize_audio(saved_path)
                        normalize_end_time = time.time()
                        normalize_duration = normalize_end_time - normalize_start_time
                        log_message(f"2. Normalizing audio: {normalize_duration:.2f} seconds")
                        
                        transcribe_start_time = time.time()
                        transcript = audio_utils.send_to_whisper(saved_path)
                        transcribe_end_time = time.time()
                        transcribe_duration = transcribe_end_time - transcribe_start_time
                        log_message(f"3. Transcribing audio: {transcribe_duration:.2f} seconds")
                        log_message(f"\nTranscription: {transcript}")
                        
                        # Reset recording state
                        is_recording = False
                        capture_thread.set_recording_state(False)
                        
                        # Return the transcript
                        return transcript
                    else:
                        log_message("Recording too short, discarding")
                    
                    # Reset recording state
                    is_recording = False
                    capture_thread.set_recording_state(False)
                    speech_start_time = None
                    silence_start_time = None
            
            # Small sleep to prevent CPU hogging
            time.sleep(0.01)
                
    except KeyboardInterrupt:
        pass
    
    return None


def is_running_as_service():
    """Check if the program is running as a systemd service."""
    # Check for INVOCATION_ID environment variable which is set by systemd
    return 'INVOCATION_ID' in os.environ or 'JOURNAL_STREAM' in os.environ

def signal_handler(sig, frame):
    """Handle signals like SIGTERM for graceful shutdown."""
    log_message("\nReceived signal to terminate. Shutting down gracefully...")
    if 'capture_thread' in globals():
        globals()['capture_thread'].stop()
        globals()['capture_thread'].join(timeout=1.0)
    sys.exit(0)

def main():
    """Main function to run the speech detection and transcription system."""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Check if running as a service
    running_as_service = is_running_as_service()
    
    log_message(f"Speech Detection and Transcription System")
    if running_as_service:
        log_message("Running as a systemd service")
    else:
        log_message("Running as a standalone application")
    log_message(f"Speech threshold: {config.DB_THRESHOLD} dB, Silence threshold: {config.SILENCE_THRESHOLD_MS} ms")
    log_message(f"Loaded {len(config.commands) if hasattr(config, 'commands') else 0} commands")
    if not running_as_service:
        log_message("Press Ctrl+C to exit")
    
    # Create and start capture thread with ring buffer
    # Buffer 10 seconds of audio (adjust as needed)
    global capture_thread  # Make it accessible to signal handler
    capture_thread = AudioCaptureThread(buffer_duration=10.0, chunk_duration=0.05)
    capture_thread.start()
    
    log_message("Audio capture thread started with ring buffer")
    
    try:
        while True:
            transcript = process_audio_and_detect_speech(capture_thread, show_volume=not running_as_service)
            if transcript:
                # Process the command and get the result
                # Temporarily set recording state to false during command processing
                # This ensures the volume meter shows LISTENING instead of RECORDING
                capture_thread.set_recording_state(False)
                
                # Process the command - this will play the confirmation sound if enabled
                api_start_time = time.time()
                success = homeassistant_utils.process_command(transcript)
                api_end_time = time.time()
                api_duration = api_end_time - api_start_time
                log_message(f"4. API request to HomeAssistant: {api_duration:.2f} seconds")
                
                # Measure time for playing confirmation sound
                if success and hasattr(config, 'PLAY_CONFIRMATION_SOUND') and config.PLAY_CONFIRMATION_SOUND:
                    if hasattr(config, 'CONFIRMATION_SOUND') and config.CONFIRMATION_SOUND:
                        sound_path = config.CONFIRMATION_SOUND
                        if os.path.exists(sound_path):
                            sound_start_time = time.time()
                            audio_utils.play_audio(sound_path)
                            sound_end_time = time.time()
                            sound_duration = sound_end_time - sound_start_time
                            log_message(f"5. Playing audio that job is finished: {sound_duration:.2f} seconds")
                
                # Give a small pause after command execution and sound playback
                # This ensures we don't immediately start recording again
                time.sleep(0.5)
            
            # Give a small pause between detection cycles
            time.sleep(0.1)
    except KeyboardInterrupt:
        log_message("\nExiting")
        # Stop the capture thread
        capture_thread.stop()
        capture_thread.join(timeout=1.0)
        sys.exit(0)

if __name__ == "__main__":
    main()
