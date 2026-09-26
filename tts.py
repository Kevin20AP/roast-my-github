"""ElevenLabs text-to-speech.

The configured voice is a library voice, which ElevenLabs blocks on free plans
(HTTP 402). When that happens we retry once with a premade voice so the demo
still has a voice; if ElevenLabs is unreachable the frontend falls back to the
browser's speechSynthesis.
"""

from __future__ import annotations

import io
import os

import requests

API = "https://api.elevenlabs.io/v1/text-to-speech"
DEFAULT_VOICE_ID = "G0yjIg3xY8gEJZkHpjVm"
DEFAULT_FALLBACK_VOICE_ID = "nPczCjzI2devNBz1zQrb"
DEFAULT_MODEL_ID = "eleven_flash_v2_5"
OUTPUT_FORMAT = "mp3_44100_128"


class VoiceError(Exception):
    """ElevenLabs could not produce audio."""


def _request(voice_id: str, text: str, api_key: str, model_id: str):
    return requests.post(
        f"{API}/{voice_id}",
        params={"output_format": OUTPUT_FORMAT},
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": model_id,
            "voice_settings": {"stability": 0.4, "similarity_boost": 0.8, "speed": 1.05},
        },
        timeout=90,
    )


def speak(text: str) -> tuple[io.BytesIO, str]:
    """Render ``text`` to mp3 bytes. Returns (audio, voice_id_used)."""
    api_key = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()
    if not api_key:
        raise VoiceError("ELEVENLABS_API_KEY is not set.")

    model_id = os.environ.get("ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID)
    primary = os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID)
    fallback = os.environ.get(
        "ELEVENLABS_FALLBACK_VOICE_ID", DEFAULT_FALLBACK_VOICE_ID
    )

    for voice_id in dict.fromkeys([primary, fallback]):
        try:
            response = _request(voice_id, text, api_key, model_id)
        except requests.RequestException as exc:
            raise VoiceError(f"ElevenLabs is unreachable: {exc}") from exc
        if response.ok:
            return io.BytesIO(response.content), voice_id
        if response.status_code not in (402, 403, 404):
            raise VoiceError(
                f"ElevenLabs returned {response.status_code}: {response.text[:200]}"
            )

    raise VoiceError(
        "ElevenLabs refused every voice we have. Falling back to the browser."
    )
