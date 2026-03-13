from __future__ import annotations

import base64
import math

_SIGN_BIT = 0x80
_QUANT_MASK = 0x0F
_SEG_SHIFT = 4
_SEG_MASK = 0x70
_BIAS = 0x84


def _search_segment(value: int) -> int:
    for segment in range(7):
        if value <= (0x1F << segment):
            return segment
    return 7


def encode_pcm16_to_mulaw_base64(pcm: bytes) -> str:
    samples = len(pcm) // 2
    mulaw = bytearray(samples)

    for i in range(samples):
        sample = int.from_bytes(pcm[i * 2 : i * 2 + 2], "little", signed=True)
        sign = _SIGN_BIT if sample < 0 else 0
        sample = abs(sample)

        if sample > 32635:
            sample = 32635

        sample += _BIAS
        segment = _search_segment(sample >> 7)
        mantissa = (sample >> (segment + 3)) & _QUANT_MASK

        encoded = ~(sign | (segment << _SEG_SHIFT) | mantissa) & 0xFF
        mulaw[i] = encoded

    return base64.b64encode(mulaw).decode("ascii")


def decode_mulaw_base64_to_pcm16(payload: str) -> bytes:
    mulaw = base64.b64decode(payload)
    pcm = bytearray(len(mulaw) * 2)

    for i, byte in enumerate(mulaw):
        byte = ~byte & 0xFF
        sign = -1 if (byte & _SIGN_BIT) else 1
        segment = (byte & _SEG_MASK) >> _SEG_SHIFT
        mantissa = byte & _QUANT_MASK
        magnitude = ((mantissa + 0.5) * (1 << (segment + 3))) - _BIAS
        sample = int(sign * magnitude)
        pcm[i * 2 : i * 2 + 2] = sample.to_bytes(2, "little", signed=True)

    return bytes(pcm)



