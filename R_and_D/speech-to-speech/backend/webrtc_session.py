import asyncio
import logging
import uuid
from typing import Awaitable, Callable, Optional

import av
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate


logger = logging.getLogger(__name__)


AudioFrameCallback = Callable[[int, bytes, int], Awaitable[None]]


class WebRTCAudioSession:
    """
    Wraps an aiortc RTCPeerConnection and forwards incoming audio frames
    to a callback after resampling to mono 16 kHz PCM.
    """

    def __init__(
        self,
        connection_id: int,
        sample_rate: int,
        frame_callback: AudioFrameCallback,
        on_ended: Optional[Callable[[str], None]] = None,
    ):
        self.id = str(uuid.uuid4())
        self.connection_id = connection_id
        self.sample_rate = sample_rate
        self.frame_callback = frame_callback
        self._on_ended = on_ended

        self.pc = RTCPeerConnection()
        self._tasks = []
        self._closed = False
        self._resampler = av.audio.resampler.AudioResampler(
            format="s16",
            layout="mono",
            rate=self.sample_rate,
        )

        @self.pc.on("track")
        async def on_track(track):
            logger.info(
                "WebRTC audio track received for connection %s (session %s)",
                self.connection_id,
                self.id,
            )
            if track.kind == "audio":
                task = asyncio.create_task(self._consume_audio(track))
                self._tasks.append(task)

        @self.pc.on("connectionstatechange")
        async def on_connection_state_change():
            logger.info(
                "WebRTC session %s connection state: %s",
                self.id,
                self.pc.connectionState,
            )
            if self.pc.connectionState in ("failed", "closed", "disconnected"):
                await self.close()

    async def _consume_audio(self, track):
        try:
            while True:
                frame = await track.recv()
                for resampled in self._resampler.resample(frame):
                    pcm = resampled.to_ndarray().tobytes()
                    await self.frame_callback(
                        self.connection_id,
                        pcm,
                        self.sample_rate,
                    )
        except asyncio.CancelledError:
            logger.debug("Audio consumer cancelled for session %s", self.id)
        except Exception as exc:
            logger.info("Audio track ended for session %s: %s", self.id, exc)

    async def accept_offer(self, offer: RTCSessionDescription) -> RTCSessionDescription:
        await self.pc.setRemoteDescription(offer)
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)
        # Wait briefly so that ICE candidates are gathered and embedded
        await asyncio.sleep(0.1)
        return self.pc.localDescription

    async def add_ice_candidate(self, candidate: Optional[dict]):
        if candidate is None:
            await self.pc.addIceCandidate(None)
            return
        rtc_candidate = RTCIceCandidate(
            sdpMid=candidate.get("sdpMid"),
            sdpMLineIndex=candidate.get("sdpMLineIndex"),
            candidate=candidate.get("candidate"),
        )
        await self.pc.addIceCandidate(rtc_candidate)

    async def close(self):
        if self._closed:
            return
        self._closed = True
        logger.info("Closing WebRTC session %s", self.id)
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self.pc.close()
        if self._on_ended:
            try:
                self._on_ended(self.id)
            except Exception as exc:
                logger.warning("Error in WebRTC on_ended callback: %s", exc)



