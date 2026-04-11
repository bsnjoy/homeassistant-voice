# p3smart RTSP Deployment

Deployment of `homeassistant-voice` that uses a Hikvision IP camera's audio
track as the microphone instead of a local USB mic, and has no local audio
playback (no aplay/TTS).

## Topology

- **Host:** `p3smart` (Debian 13, root user, `~/homeassistant-voice`)
- **Audio sources (two cameras in the same room, processed in parallel):**
  - `192.168.1.205` — `rtsp://admin:love2918@192.168.1.205:554/Streaming/Channels/102`
  - `192.168.1.208` — `rtsp://admin:love2918@192.168.1.208:554/Streaming/Channels/102`

  Each runs in its own `SpeechSource` thread with an independent ffmpeg
  process. Whichever mic captures a given utterance first wins; identical
  commands seen within `DEDUPE_WINDOW_SEC` (default 2 s) from the second
  mic are dropped by the main-loop dedupe.
  Audio tracks are 16 kHz mono AAC — matches `SAMPLE_RATE`, no resampling
  needed on the detection side.
- **Transcription:** `transcription-api.service` on the same host at
  `http://127.0.0.1:8889/transcribe` (GigaAM, Russian).
- **Home Assistant:** `http://192.168.1.66:8123`, controlled via long-lived
  access token stored in `config.py`.
- **Playback:** none. p3smart has no speakers, `HOMEASSISTANT_SOUND` /
  `AI_SOUND` are empty strings so `audio.play_audio` is a no-op.

## Audio pipeline

Instead of `arecord`, `config.AUDIO_RECORD_CMDS` launches one ffmpeg
process per camera; each becomes a `SpeechSource` thread reading raw
s16le from its ffmpeg's stdout:

```
ffmpeg -loglevel quiet -rtsp_transport tcp \
  -i rtsp://admin:love2918@192.168.1.205:554/Streaming/Channels/102 \
  -vn -acodec pcm_s16le -ar 16000 -ac 1 -f s16le -
```

No code changes are required to add more mics — only extra entries in
`AUDIO_RECORD_CMDS`.

## Commands configured

| Phrase | Action | Entities |
| --- | --- | --- |
| `включи/выключи свет` | `turn_on` / `turn_off` | `switch.living_light` (default room = `living_room`) |
| `включи/выключи свет в саду` | `turn_on` / `turn_off` | `switch.garden_switch` **and** `switch.garden_switch_2` (single HA call with list payload) |

The garden case relies on `send_homeassistant_command` accepting a list of
entity IDs that share a domain (commit `00b7998`).

## Install / update

Clone and pull via git (not rsync — keep the working tree tracked):

```bash
# first-time install on p3smart
ssh p3smart 'git clone p3git:homeassistant-voice.git ~/homeassistant-voice'

# update
ssh p3smart 'cd ~/homeassistant-voice && git pull && systemctl restart homeassistant-voice'
```

Dependencies are installed system-wide via apt (no venv — Debian 13
`python3-venv` is not present on this host and nothing else on the host
competes for these packages):

```bash
ssh p3smart 'apt-get install -y python3-numpy python3-requests python3-openai ffmpeg'
```

`python3-openai` is installed only so `from utils import ai` succeeds — the
AI branch is never taken because no wake word (`умник` / `бобер`) appears
in camera audio.

## `config.py`

Not tracked in git — lives only on p3smart at
`/root/homeassistant-voice/config.py`. Key values:

```python
TRANSCRIPTION_API_URL = "http://127.0.0.1:8889/transcribe"
HOMEASSISTANT_URL     = "http://192.168.1.66:8123"
HOMEASSISTANT_TOKEN   = "<long-lived token>"

HOMEASSISTANT_SOUND = ""   # no speakers
AI_SOUND            = ""
VOICE_PLAY_CMD      = ["true"]
AUDIO_PLAY_CMD      = ["true"]

def _ffmpeg_rtsp(url):
    return [
        "ffmpeg", "-loglevel", "quiet", "-rtsp_transport", "tcp",
        "-i", url,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        "-f", "s16le", "-",
    ]

AUDIO_RECORD_CMDS = {
    "cam205": _ffmpeg_rtsp("rtsp://admin:love2918@192.168.1.205:554/Streaming/Channels/102"),
    "cam208": _ffmpeg_rtsp("rtsp://admin:love2918@192.168.1.208:554/Streaming/Channels/102"),
}
DEDUPE_WINDOW_SEC = 2.0

default_room = "living_room"
device_aliases = {"light": ["свет", "лампа", "light", "lamp"]}
room_aliases = {
    "living_room": ["living room", "гостиная", "гостиной"],
    "garden":      ["garden", "сад", "саду", "саде"],
}
room_entities = {
    "living_room": {"light": "switch.living_light"},
    "garden":      {"light": ["switch.garden_switch", "switch.garden_switch_2"]},
}
```

## systemd unit

`/etc/systemd/system/homeassistant-voice.service` on p3smart:

```ini
[Unit]
Description=Home Assistant Voice Service (RTSP)
After=network-online.target transcription-api.service
Wants=network-online.target
Requires=transcription-api.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/homeassistant-voice
ExecStart=/usr/bin/python3 /root/homeassistant-voice/main.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

`Requires=transcription-api.service` ties the voice service to the local
GigaAM server — if that is down, this one will not start.

## Operations

```bash
# live log (all output)
ssh p3smart 'journalctl -u homeassistant-voice -f'

# live transcripts only
ssh p3smart 'journalctl -u homeassistant-voice -f -o cat' | grep --line-buffered Transcript

# restart
ssh p3smart 'systemctl restart homeassistant-voice'
```

If the camera stream picks up too much ambient noise and the log fills
with empty `Transcript:` lines, raise `DB_THRESHOLD` in `config.py` and
restart.
