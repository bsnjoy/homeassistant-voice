#!/usr/bin/env python3
from pathlib import Path

import httpx

client = httpx.Client(base_url="http://192.168.1.65:8000/")
res = client.post(
    "v1/audio/speech",
    json={
        "model": "rhasspy/piper-voices",
        "voice": "ru_RU-ruslan-medium",
        "input": "Привет, это тестовое сообщение для преобразования текста в речь.",
        "response_format": "mp3",
        "speed": 1,
    },
).raise_for_status()
with Path("output.mp3").open("wb") as f:
    f.write(res.read())