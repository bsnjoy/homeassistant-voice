# Home Assistant Voice Control

A voice-controlled system for Home Assistant that listens for spoken commands, transcribes them using Whisper API, and sends the appropriate commands to your Home Assistant instance.

## Features

- **Continuous Audio Monitoring**: Listens for speech using any process that writes raw s16le to stdout (local `arecord`/`parecord` or `ffmpeg` from an RTSP camera)
- **Speech Detection**: Automatically detects when someone is speaking based on volume threshold
- **Speech-to-Text**: Transcribes spoken commands via a pluggable HTTP API (GigaAM or Whisper)
- **Command Processing**: Parses transcribed text to identify actions, devices, and rooms
- **Home Assistant Integration**: Sends commands to Home Assistant via its REST API, with support for toggling multiple entities in a single call
- **Audio Feedback**: Optional Piper TTS and confirmation sounds (can be disabled on hosts without speakers)
- **Systemd Service**: Can be run as a background service on Linux systems

## Requirements

- Python 3.6+
- One of: ALSA/PulseAudio for a local mic, or `ffmpeg` for an RTSP camera audio track
- A transcription HTTP endpoint (GigaAM or Whisper), local or remote
- Home Assistant instance with API access
- Optional: Piper TTS server for spoken responses

## Dependencies

- numpy
- requests
- openai (only if the AI assistant wake-word branch is used)

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
   - Home Assistant URL and access token. Generate Long-lived access token in the bottom of http://homeassistant.local:8123/profile/security
   - Audio recording settings
   - Commands and device mappings

## Configuration

The `config.py` file contains all the configuration options:

### Transcription API Configuration
```python
TRANSCRIPTION_API_URL = "http://your-transcription-server:8889/transcribe"
```
The server is expected to accept a multipart `audio` file and return JSON
`{"text": "..."}`. Any backend that speaks that contract works — see the
`transcription_api` project (GigaAM) or a Whisper-compatible server.

### Audio Source Configuration
```python
# Local ALSA mic:
AUDIO_RECORD_CMD = ["arecord", "-D", "dsnoop:CARD=MS,DEV=0",
                    "-r", "16000", "-c", "1", "-f", "S16_LE", "-t", "raw"]

# Or a Hikvision RTSP camera audio track:
AUDIO_RECORD_CMD = [
    "ffmpeg", "-loglevel", "quiet", "-rtsp_transport", "tcp",
    "-i", "rtsp://user:pass@camera.local:554/Streaming/Channels/102",
    "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
    "-f", "s16le", "-",
]
```
Anything that writes raw `s16le` @ `SAMPLE_RATE` to stdout will work.

### Home Assistant Configuration
```python
HOMEASSISTANT_URL = "http://your-homeassistant:8123"
HOMEASSISTANT_TOKEN = "YOUR_LONG_LIVED_ACCESS_TOKEN"
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

Map devices to Home Assistant entity IDs. A device may be mapped to a
single entity ID or to a **list** of entity IDs that share a domain — a
single voice command will then toggle all of them in one HA API call.

```python
room_entities = {
    "office": {
        "ac": "climate.office_ac",
        "light": "light.office_main",
    },
    "garden": {
        # Two-relay switch — one command hits both outputs
        "light": ["switch.garden_switch", "switch.garden_switch_2"],
    },
}
```

#### "Everywhere" / cross-room commands

To make a phrase like `включи везде свет` (or `turn on the light
everywhere`) trigger every room's light at once, add a **virtual room**
to `room_aliases` and `room_entities` whose device entry is a flat list
of every entity to hit. No code changes needed — the existing room
matching plus list-entity fan-out already does it.

```python
room_aliases = {
    "office":     ["office", "офис"],
    "garden":     ["garden", "сад", "саду"],
    "everywhere": ["everywhere", "везде"],
}

room_entities = {
    "office":  {"light": "light.office_main"},
    "garden":  {"light": ["switch.garden_switch", "switch.garden_switch_2"]},
    "everywhere": {
        "light": [
            "light.office_main",
            "switch.garden_switch", "switch.garden_switch_2",
        ],
    },
}
```

Keep the `everywhere` lists in sync when adding entities to real rooms.
All entities in one list must share a domain.

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
5. Check logs:
   ```
   sudo journalctl -u homeassistant-voice.service
   
   # To see only the most recent logs:
   sudo journalctl -u homeassistant-voice.service -n 50
   
   # To follow the logs in real-time (like tail -f):
   sudo journalctl -u homeassistant-voice.service -f
   
   # To see logs since the last boot:
   sudo journalctl -u homeassistant-voice.service -b
   ```

### Service Management and Graceful Shutdown

The service supports graceful shutdown when stopped or restarted via systemctl:

```bash
# Stop the service
sudo systemctl stop homeassistant-voice.service

# Restart the service
sudo systemctl restart homeassistant-voice.service
```

When the service receives a shutdown signal (SIGTERM):
1. It stops accepting new voice commands
2. Stops the audio capture thread cleanly
3. Stops any currently playing TTS audio
4. Clears any pending TTS queue items
5. Exits gracefully with proper cleanup

This ensures that:
- No audio processes are left running
- No partial recordings are processed
- The service can be restarted cleanly without issues

You can test the shutdown behavior using the included test script:
```bash
python tests/test_shutdown.py
```

This will verify that the service handles shutdown signals correctly.

### add usb device monitoring
disconnect and connect speaker and monitor dmesg for device id added.
```
dmesg
```

```
cp report.sh.sample report.sh
sudo cp 99-usb-jabra.rules /etc/udev/rules.d/
```

Edit
vim /etc/udev/rules.d/99-usb-jabra.rules - to fix script with correct device id and copy to rules
vim report.sh - put your telegram bot token and your id.
```
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Testing

#### Running All Tests

To run all tests in the tests directory:

```bash
python run_tests.py
```

#### Individual Test Scripts

- **Test Shutdown Behavior**: `python tests/test_shutdown.py`
- **Test TTS Functionality**: `python tests/test_tts.py`
- **Test TTS Debug Mode**: `python tests/test_tts_debug.py`
- **Test AI Integration**: Run via `python run_tests.py` (unit test)

#### Testing Transcription

You can test the transcription functionality separately:

```
python transcribe.py recordings/your-recording.wav
```

### Controlling an entity from the command line (`ha.py`)

`ha.py` is a small helper that calls the Home Assistant REST API using
the URL and token from `config.py`. Useful when you need to probe which
relay is which (e.g. identifying the two outputs on a dual-relay switch
like `terrace_strip_poolceiling_light`) or to script a quick toggle
outside the voice pipeline.

```
# Toggle (no second argument)
./ha.py switch.terrace_toilet_light

# Explicit on / off (accepts on|1|true and off|0|false)
./ha.py switch.terrace_fan_switch on
./ha.py switch.terrace_fan_switch_2 off
./ha.py light.office_main 1
./ha.py climate.office_ac 0
```

The entity's domain (`switch`, `light`, `climate`, …) is inferred from
the part before the dot, so any entity that supports
`turn_on`/`turn_off`/`toggle` works.

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

## Deployments

- **p3smart (RTSP from Hikvision camera, no local playback):**
  docs/p3smart-rtsp-deployment.md

Project overview and conventions for contributors: CLAUDE.md

## License

[Your License Here]
