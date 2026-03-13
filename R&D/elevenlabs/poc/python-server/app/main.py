from __future__ import annotations

from fastapi import FastAPI, Response, WebSocket
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.services.bridge import ElevenLabsConfig, TwilioElevenLabsBridgeSession

app = FastAPI()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/voice", response_class=PlainTextResponse)
async def voice_webhook() -> Response:
    stream_url = settings.resolved_twilio_stream_url
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        "<Connect>"
        f'<Stream url="{stream_url}" track="inbound_track" />'
        "</Connect>"
        "</Response>"
    )
    return Response(content=twiml, media_type="text/xml")


@app.websocket("/twilio-media-stream")
async def twilio_media_stream(ws: WebSocket) -> None:
    config = ElevenLabsConfig(
        api_key=settings.elevenlabs_api_key,
        agent_id=settings.elevenlabs_agent_id,
        base_url=settings.elevenlabs_realtime_url,
    )
    session = TwilioElevenLabsBridgeSession(ws, config)
    try:
        await session.run()
    except Exception as exc:
        print("[Bridge] Session ended with error:", exc)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=True)

