"""
Audio conversion helpers.

Provides utilities to convert browser-recorded WebM/Opus audio
into 16 kHz mono PCM bytes that Vosk can consume.
"""
from __future__ import annotations

import base64
import shutil
import subprocess
from typing import Optional


class AudioConversionError(RuntimeError):
    """Raised when audio conversion fails."""


def ensure_ffmpeg_available(ffmpeg_binary: str = "ffmpeg") -> str:
    """
    Ensure ffmpeg binary exists on PATH.

    Args:
        ffmpeg_binary: Preferred binary name/path.

    Returns:
        str: Resolved path to ffmpeg executable.

    Raises:
        AudioConversionError: if ffmpeg is not found.
    """
    resolved = shutil.which(ffmpeg_binary)
    if not resolved:
        raise AudioConversionError(
            "ffmpeg binary not found. Please install ffmpeg and ensure it is available on PATH."
        )
    return resolved


def webm_base64_to_pcm(
    audio_base64: str,
    sample_rate: int = 16000,
    ffmpeg_binary: Optional[str] = None,
) -> bytes:
    """
    Convert a base64-encoded WebM/Opus audio blob to 16 kHz mono PCM bytes.

    Args:
        audio_base64: Base64 string produced by MediaRecorder (audio/webm).
        sample_rate: Target PCM sample rate.
        ffmpeg_binary: Optional explicit path to ffmpeg.

    Returns:
        bytes: Raw PCM (s16le) samples suitable for Vosk.

    Raises:
        AudioConversionError: if conversion fails.
    """
    ffmpeg_path = ensure_ffmpeg_available(ffmpeg_binary or "ffmpeg")

    try:
        audio_bytes = base64.b64decode(audio_base64)
    except Exception as exc:  # base64 decoding errors
        raise AudioConversionError(f"Unable to decode audio payload: {exc}") from exc

    try:
        process = subprocess.run(
            [
                ffmpeg_path,
                "-loglevel",
                "error",
                "-i",
                "pipe:0",
                "-f",
                "s16le",
                "-acodec",
                "pcm_s16le",
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                "pipe:1",
            ],
            input=audio_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="ignore")
        raise AudioConversionError(
            f"ffmpeg failed to convert audio chunk: {stderr.strip()}"
        ) from exc
    except FileNotFoundError as exc:
        raise AudioConversionError(
            "ffmpeg executable not found. Install ffmpeg and add it to PATH."
        ) from exc

    pcm_data = process.stdout
    if not pcm_data:
        raise AudioConversionError("ffmpeg returned empty audio payload.")

    return pcm_data


