# homeassistant-voice

Voice control for Home Assistant: capture audio → detect speech → transcribe
(GigaAM/Whisper) → match action/device/room aliases → call HA REST API.

Entry point: `main.py`. Each audio input runs in its own `SpeechSource`
thread that spawns a subprocess writing raw s16le to stdout, detects speech
by dB threshold, transcribes the utterance, and pushes the result onto a
shared queue. The main loop reads from the queue, matches commands via
`utils.homeassistant.process_command`, and dedupes repeated commands (same
entity + action) inside `DEDUPE_WINDOW_SEC` (default 2 s) so two mics in
the same room don't trigger twice.

Configure one or many sources via `config.AUDIO_RECORD_CMD` (single) or
`config.AUDIO_RECORD_CMDS` (list of commands, or dict `{name: cmd}` for
nicer log labels). Swap the command to change the audio source — local
`arecord` / `parecord` or `ffmpeg` from an RTSP stream — without touching
code.

## Deployments

- **p3smart (RTSP from Hikvision camera, no local playback)** —
  docs/p3smart-rtsp-deployment.md
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
- A `room_entities[room][device]` value may also be a `{action: entity(s)}`
  dict when one action should target a different set than another (e.g. the
  pool `light` whose `turn_off` also kills the jacuzzi while `turn_on`
  doesn't). `process_command` resolves the dict by the spoken action, falling
  back to a `"default"` key if present. Prefer this over special-casing in
  `process_command`.
- **Cross-room / "everywhere" commands are config, not code.** When you
  need a phrase like `включи везде свет` to hit every room's light, add
  a virtual room (e.g. `"everywhere"`) to `room_aliases` and `room_entities`
  whose device entry is a flat list of every entity to trigger. The
  existing room-match + list-entity fan-out handles the rest — do **not**
  add special-case logic in `process_command`.
