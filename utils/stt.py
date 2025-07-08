import requests
import config
import io
from utils.timing import time_execution
from datetime import datetime
import wave

def wrap_raw_pcm_as_wav(raw_audio, sample_rate=16000, num_channels=1, sample_width=2):
    """
    Wrap raw PCM data as a valid WAV file in memory.
    """
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(sample_width)  # 2 bytes = 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(raw_audio)
    buffer.seek(0)
    return buffer


@time_execution(label="Transcribing audio")
def transcribe(audio_input):
    """
    Send audio to Whisper API for transcription.

    Parameters:
    - audio_input: Either a file path (str) or raw audio data (bytes)

    Returns:
    - The transcription result if successful
    - None if an error occurred
    """
    try:
        if isinstance(audio_input, str):
            # File path - open and read the file
            files = {"audio": open(audio_input, "rb")}
        else:
            # Create proper WAV file from raw PCM
            wav_buffer = wrap_raw_pcm_as_wav(audio_input)
            # Generate filename using current timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"world_audio_{timestamp}.wav"
            # Raw audio data - provide filename and content type
            files = {
                "audio": (filename, wav_buffer, "audio/wav")
            }
            print(f"Transcribing raw audio data with virtual filename: {filename}")

        response = requests.post(config.TRANSCRIPTION_API_URL, files=files)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json().get("text", None)  # Extract the transcription text from the response
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        if isinstance(audio_input, str):
            files["audio"].close()  # Make sure to close the file if it was opened
