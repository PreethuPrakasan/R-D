from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

import contextlib

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from app.services.elevenlabs import ElevenLabsRealtimeClient
from app.utils.audio import decode_mulaw_base64_to_pcm16, encode_pcm16_to_mulaw_base64


@dataclass
class ElevenLabsConfig:
    api_key: str
    agent_id: str
    base_url: str


class TwilioElevenLabsBridgeSession:
    def __init__(self, websocket: WebSocket, config: ElevenLabsConfig) -> None:
        self._ws = websocket
        self._stream_sid: str | None = None
        self._ready = asyncio.Event()
        self._closed = asyncio.Event()
        self._eleven_client = ElevenLabsRealtimeClient(
            api_key=config.api_key,
            agent_id=config.agent_id,
            base_url=config.base_url,
            on_audio=self._send_audio_to_twilio,
            on_message=self._log_agent_message,
        )

    async def run(self) -> None:
        await self._ws.accept(subprotocol="audio")
        try:
            while True:
                packet = await self._ws.receive_text()
                await self._handle_twilio_packet(packet)
        except WebSocketDisconnect:
            await self._cleanup()
        except Exception:
            await self._cleanup()
            raise
        finally:
            await self._cleanup()

    async def _handle_twilio_packet(self, packet: str) -> None:
        try:
            data = json.loads(packet)
        except json.JSONDecodeError:
            return
        event = data.get("event")

        if event == "start":
            self._stream_sid = data.get("streamSid")
            await self._eleven_client.connect()
            self._ready.set()
            return

        if event == "media":
            if not self._ready.is_set():
                return
            payload = data["media"]["payload"]
            if not payload:
                return
            pcm = decode_mulaw_base64_to_pcm16(payload)
            await self._eleven_client.send_audio(pcm)
            return

        if event == "stop":
            await self._cleanup()
            return

    async def _send_audio_to_twilio(self, audio: bytes) -> None:
        await self._ready.wait()
        if not self._stream_sid:
            return
        payload = encode_pcm16_to_mulaw_base64(audio)
        message = {
            "event": "media",
            "streamSid": self._stream_sid,
            "media": {
                "payload": payload,
            },
        }
        await self._ws.send_text(json.dumps(message))

    async def _log_agent_message(self, payload: dict[str, Any]) -> None:
        event_type = payload.get("type")
        if event_type in {"transcript.delta", "response.completed"}:
            print("[ElevenLabs]", json.dumps(payload))

    async def _cleanup(self) -> None:
        if not self._closed.is_set():
            self._closed.set()
            await self._eleven_client.close()
            with contextlib.suppress(RuntimeError):
                await self._ws.close()

