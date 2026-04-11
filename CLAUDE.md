# homeassistant-voice

Voice control for Home Assistant: capture audio → detect speech → transcribe
(GigaAM/Whisper) → match action/device/room aliases → call HA REST API.

Entry point: `main.py` (ring-buffer `AudioCaptureThread` in the same file).
Audio capture is a subprocess launched from `config.AUDIO_RECORD_CMD` that
writes raw s16le to stdout — swap that command to change the audio source
(local `arecord`, `parecord`, or `ffmpeg` from an RTSP stream) without
touching code.

## Deployments

- **p3smart (RTSP from Hikvision camera, no local playback)** —
  docs/p3smart-rtsp-deployment.md.
  Uses `ffmpeg` to pull the camera audio track as the mic, transcribes via
  the local `transcription-api.service`, toggles `switch.living_light` and
  the two garden relays.

## Conventions

- `config.py` is **not** tracked — each deployment has its own. Start from
  `config.py.sample`.
- To ship a code change to a deployment host, commit + push + `git pull` on
  the host. Do not rsync working-tree files.
- `send_homeassistant_command(entity_id, service)` accepts either a string
  or a list of entity IDs sharing a domain; `config.room_entities` may map
  a device to a list when one logical command should hit several entities.
