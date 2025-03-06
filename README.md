# Home Assistant Voice Control

A voice-controlled system for Home Assistant that listens for spoken commands, transcribes them using Whisper API, and sends the appropriate commands to your Home Assistant instance.

## Features

- **Continuous Audio Monitoring**: Listens for speech using your microphone
- **Speech Detection**: Automatically detects when someone is speaking based on volume threshold
- **Speech-to-Text**: Transcribes spoken commands using Whisper API
- **Command Processing**: Parses transcribed text to identify actions, devices, and rooms
- **Home Assistant Integration**: Sends commands to Home Assistant via its REST API
- **Audio Feedback**: Plays confirmation sounds when commands are successfully executed
- **Systemd Service**: Can be run as a background service on Linux systems

## Requirements

- Python 3.6+
- ALSA or PulseAudio for audio capture
- Sox for audio normalization (optional but recommended)
- Whisper API server (local or remote)
- Home Assistant instance with API access

## Dependencies

- numpy
- requests

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/homeassistant-voice.git
   cd homeassistant-voice
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a configuration file:
   ```
   cp config.py.sample config.py
   ```

5. Edit `config.py` to configure your:
   - Whisper API settings
   - Home Assistant URL and access token
   - Audio recording settings
   - Commands and device mappings

## Configuration

The `config.py` file contains all the configuration options:

### Whisper API Configuration
```python
model = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"
prompt = "включи выключи свет в офисе"
language = "ru"
response_format = "text"
server_url = "http://your-whisper-server:8000"
```

### Home Assistant Configuration
```python
homeassistant_url = "http://your-homeassistant:8123"
homeassistant_token = "YOUR_LONG_LIVED_ACCESS_TOKEN"
```

### Audio Configuration
```python
RECORDINGS_DIR = "recordings"
DB_THRESHOLD = 50  # Speech detection threshold in dB
SILENCE_THRESHOLD_MS = 500  # Silence duration threshold in ms
MIN_RECORDING_LENGTH_SEC = 1.0  # Minimum recording length to process
```

### Command Configuration

Define aliases for actions, devices, and rooms:

```python
# Action aliases (turn on/off)
action_aliases = {
    "turn_on": ["turn on", "enable", "start", "включи", "включить"],
    "turn_off": ["turn off", "disable", "stop", "выключи", "выключить"]
}

# Device aliases
device_aliases = {
    "ac": ["ac", "air conditioner", "air conditioning", "кондиционер"],
    "light": ["light", "lamp", "свет", "лампа"],
    "tv": ["tv", "television", "телевизор"]
}

# Room aliases
room_aliases = {
    "office": ["office", "офис", "кабинет"],
    "bedroom": ["bedroom", "спальня"],
    "living_room": ["living room", "гостиная"]
}
```

Map devices to Home Assistant entity IDs:

```python
# Room to device mapping
room_entities = {
    "office": {
        "ac": "climate.office_ac",
        "light": "light.office_main",
    },
    "bedroom": {
        "ac": "climate.bedroom_ac",
        "light": "light.bedroom_main",
    },
}
```

## Usage

### Running Manually

```
python main.py
```

The program will start listening for voice commands. When it detects speech, it will:
1. Record the audio
2. Transcribe it using Whisper API
3. Process the transcription to identify commands
4. Send the appropriate command to Home Assistant
5. Play a confirmation sound if the command was successful

### Running as a Service

1. Edit the `homeassistant-voice.service` file to match your installation path
2. Copy the service file to systemd:
   ```
   sudo cp homeassistant-voice.service /etc/systemd/system/
   ```
3. Enable and start the service:
   ```
   sudo systemctl enable homeassistant-voice.service
   sudo systemctl start homeassistant-voice.service
   ```
4. Check the status:
   ```
   sudo systemctl status homeassistant-voice.service
   ```

### Testing Transcription

You can test the transcription functionality separately:

```
python transcribe.py recordings/your-recording.wav
```

## Voice Command Format

The system recognizes commands in the format:
- `[action] [device] in [room]`

Examples:
- "Turn on the light in the office"
- "Turn off the AC in the bedroom"
- "Turn on the TV"

The room is optional if the device is configured in `devices_without_room`.

## Troubleshooting

### Audio Issues

- Make sure your microphone is properly connected and configured
- Adjust the `DB_THRESHOLD` value in `config.py` if speech detection is too sensitive or not sensitive enough
- Check the ALSA/PulseAudio configuration in `config.py` to match your system

### Transcription Issues

- Verify that your Whisper API server is running and accessible
- Check the server logs for any errors
- Try testing with the `transcribe.py` script to isolate issues

### Home Assistant Issues

- Verify that your Home Assistant URL and token are correct
- Check that the entity IDs in your configuration match those in Home Assistant
- Ensure that your Home Assistant instance is running and accessible

## License

[Your License Here]
