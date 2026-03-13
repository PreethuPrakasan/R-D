import os
from io import BytesIO
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import requests
from werkzeug.utils import secure_filename

"""
Simple Flask server to proxy Deepgram API for testing.

Endpoints:
  - POST /api/tts
      JSON: { "text": "Hello world", "model": "aura-asteria-en", "format": "mp3" }
      Returns: audio bytes (audio/mpeg by default)
  - POST /api/chat
      JSON: { "message": "..." }
      Returns: { reply: "..." } from LLM (if OPENAI_API_KEY is set), else a simple placeholder
  - POST /api/stt
      multipart/form-data with 'audio' file → { transcript, raw }

Environment:
  - DEEPGRAM_API_KEY: required
  - OPENAI_API_KEY: optional (enables real chat responses via OpenAI)
  - OPENAI_MODEL: optional (defaults to gpt-4o-mini or gpt-3.5-turbo if not available)
"""

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
DEFAULT_TTS_MODEL = "aura-asteria-en"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

app = Flask(__name__)
CORS(app)


@app.route("/api/health", methods=["GET"])
def health() -> Response:
    return jsonify({"ok": True, "deepgram_key": bool(DEEPGRAM_API_KEY)})


@app.route("/api/tts", methods=["POST"])
def tts() -> Response:
    if not DEEPGRAM_API_KEY:
        return jsonify({"error": "DEEPGRAM_API_KEY not set"}), 400

    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    model = data.get("model", DEFAULT_TTS_MODEL)
    fmt = data.get("format", "mp3").lower()  # mp3/ogg/wav

    if not text:
        return jsonify({"error": "Missing 'text'"}), 400

    url = f"https://api.deepgram.com/v1/speak?model={model}"
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "application/json",
        # Deepgram returns audio based on Accept header; mp3 is default in practice, but we can hint
        "Accept": "audio/mpeg" if fmt == "mp3" else "application/octet-stream",
    }

    try:
        dg_resp = requests.post(url, headers=headers, json={"text": text}, timeout=60)
        if dg_resp.status_code >= 400:
            return jsonify({"error": "Deepgram error", "status": dg_resp.status_code, "body": dg_resp.text}), 502

        audio_bytes = BytesIO(dg_resp.content).getvalue()
        mimetype = "audio/mpeg" if fmt == "mp3" else "application/octet-stream"
        return Response(audio_bytes, mimetype=mimetype)
    except requests.RequestException as e:
        return jsonify({"error": "RequestException", "message": str(e)}), 502


@app.route("/api/chat", methods=["POST"])
def chat() -> Response:
    """
    Chat endpoint.
    If OPENAI_API_KEY is set, proxy to OpenAI Chat Completions for real replies.
    Otherwise, return a simple rule-based placeholder.
    """
    data = request.get_json(silent=True) or {}
    user = (data.get("message") or "").strip().lower()
    if not user:
        return jsonify({"reply": "Can you repeat that?"})

    # If an LLM key is available, call it for a real reply
    if OPENAI_API_KEY:
        try:
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            }
            # Some environments may not have 4o-mini; fall back automatically
            model = OPENAI_MODEL or "gpt-4o-mini"
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a concise assistant. Answer helpfully in one or two sentences."},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.5,
            }
            r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
            if r.status_code >= 400:
                # Fall back to placeholder on error
                return jsonify({"reply": "I'm having trouble contacting the model. Please try again."}), 200
            data = r.json()
            reply = data["choices"][0]["message"]["content"].strip()
            return jsonify({"reply": reply})
        except Exception:
            return jsonify({"reply": "I ran into an issue generating a response."}), 200

    # Naive rules for demo purposes
    if any(k in user for k in ["hi", "hello", "hey"]):
        reply = "Hello! How can I help you today?"
    elif "time" in user:
        from datetime import datetime
        reply = f"It's {datetime.now().strftime('%I:%M %p')} right now."
    elif "name" in user:
        reply = "I'm a demo assistant wired for Deepgram testing."
    elif "help" in user:
        reply = "You can ask me for the time, or just say hello."
    else:
        reply = "Got it. For now I'm a simple demo—try asking for the time."

    return jsonify({"reply": reply})


@app.route("/api/stt", methods=["POST"])
def stt() -> Response:
    """
    Transcribe short audio chunks using Deepgram's pre-recorded API.
    Accepts multipart/form-data with 'audio' file (webm/wav/mp3).
    """
    if not DEEPGRAM_API_KEY:
        return jsonify({"error": "DEEPGRAM_API_KEY not set"}), 400

    if "audio" not in request.files:
        return jsonify({"error": "No 'audio' file provided"}), 400

    audio = request.files["audio"]
    filename = secure_filename(audio.filename or "audio.webm")
    content = audio.read()

    # Heuristic content-type
    # Preserve full mimetype if available (e.g., audio/webm;codecs=opus)
    ctype = audio.mimetype or "audio/webm"

    params = {
        "smart_format": "true",
        "punctuate": "true",
    }
    url = "https://api.deepgram.com/v1/listen"
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": ctype,
    }
    try:
        dg_resp = requests.post(url, params=params, headers=headers, data=content, timeout=60)
        if dg_resp.status_code >= 400:
            return jsonify({"error": "Deepgram STT error", "status": dg_resp.status_code, "body": dg_resp.text}), 502
        dg_json = dg_resp.json()
        # Extract best transcript
        transcript = ""
        try:
            transcript = dg_json["results"]["channels"][0]["alternatives"][0]["transcript"]
        except Exception:
            transcript = ""
        return jsonify({"transcript": transcript, "raw": dg_json})
    except requests.RequestException as e:
        return jsonify({"error": "RequestException", "message": str(e)}), 502

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5050"))
    # Run with: python server.py
    # Ensure DEEPGRAM_API_KEY is set in your environment.
    app.run(host="0.0.0.0", port=port, debug=True)


