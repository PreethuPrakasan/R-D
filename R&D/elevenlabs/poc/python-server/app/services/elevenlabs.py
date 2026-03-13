from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Awaitable, Callable
from typing import Any

import websockets
from websockets.typing import Data


class ElevenLabsRealtimeClient:
    def __init__(
        self,
        *,
        api_key: str,
        agent_id: str,
        base_url: str,
        on_audio: Callable[[bytes], Awaitable[None]],
        on_message: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> None:
        self._api_key = api_key
        self._agent_id = agent_id
        self._base_url = base_url
        self._on_audio = on_audio
        self._on_message = on_message
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._receive_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        async with self._lock:
            if self._ws and self._ws.open:
                return

            self._ws = await websockets.connect(
                self._base_url,
                extra_headers={
                    "xi-api-key": self._api_key,
                    "x-agent-id": self._agent_id,
                },
            )

            await self._initialize_session()
            self._receive_task = asyncio.create_task(self._receive_loop())

    async def _initialize_session(self) -> None:
        payload = {
            "type": "session.update",
            "session": {
                "agent_id": self._agent_id,
                "modalities": ["text", "audio"],
            },
        }
        await self.send_json(payload)

    async def send_json(self, payload: dict[str, Any]) -> None:
        if not self._ws:
            raise RuntimeError("WebSocket not connected")
        await self._ws.send(json.dumps(payload))

    async def send_audio(self, chunk: bytes) -> None:
        if not self._ws:
            raise RuntimeError("WebSocket not connected")
        await self._ws.send(chunk)

    async def close(self) -> None:
        async with self._lock:
            if self._receive_task:
                self._receive_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._receive_task
                self._receive_task = None
            if self._ws:
                await self._ws.close()
                self._ws = None

    async def _receive_loop(self) -> None:
        assert self._ws
        ws = self._ws
        try:
            async for message in ws:
                await self._handle_message(message)
        except websockets.ConnectionClosed:
            pass

    async def _handle_message(self, data: Data) -> None:
        if isinstance(data, (bytes, bytearray, memoryview)):
            await self._on_audio(bytes(data))
            return

        if isinstance(data, str):
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                return
            if self._on_message:
                await self._on_message(payload)

import contextlib

