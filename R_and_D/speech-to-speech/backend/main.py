"""
Main FastAPI Server for Speech-to-Speech Application
"""
import asyncio
import base64
import io
import json
import logging
import os
import re
import struct
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from aiortc import RTCSessionDescription  # type: ignore
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from pydantic import BaseModel

from asr.whisper_asr import WhisperASR
from llm.ollama_llm import OllamaLLM
from tts.piper_tts import PiperTTS
from utils.audio_utils import AudioConversionError, webm_base64_to_pcm, webm_chunks_to_pcm
from webrtc_session import WebRTCAudioSession

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
# Enable debug logging for main module
logger.setLevel(logging.DEBUG)

# Initialize FastAPI app
app = FastAPI(title="Speech-to-Speech API", version="1.0.0")

# CORS middleware
# Allow all origins for mobile app compatibility
# In production, restrict to specific origins for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (mobile apps don't have specific origins)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
asr_engine: Optional[WhisperASR] = None
llm_engine: Optional[OllamaLLM] = None
tts_engine: Optional[PiperTTS] = None

# Audio buffers for streaming (per connection)
audio_buffers: Dict[int, Dict] = {}
silence_threshold = 2.0  # 2 seconds of silence before processing
max_buffer_duration = 10.0  # Maximum seconds of audio to keep in buffer
DEFAULT_SAMPLE_RATE = 16000

# Connection registries
websocket_connections: Dict[int, WebSocket] = {}
webrtc_sessions: Dict[str, WebRTCAudioSession] = {}

# Energy/VAD settings
MIN_SPEECH_ENERGY = 200  # Minimum RMS energy to consider speech
ENERGY_MARGIN = 150      # Additional energy above noise floor required
PRE_ROLL_CHUNKS = 4      # Number of silent chunks to keep before speech starts

# Configuration
CONFIG_PATH = Path(__file__).parent / "config" / "agent_config.json"


def load_config() -> dict:
    """Load agent configuration"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {
            "agent_role": "Assistant",
            "agent_description": "A helpful AI assistant",
            "tone": "Friendly",
            "language": "English"
        }


def create_audio_buffer() -> Dict[str, Any]:
    return {
        'chunks': [],
        'pcm_chunks': [],
        'chunk_timestamps': [],
        'speech_chunk_times': [],
        'pre_speech_buffer': [],
        'noise_floor': None,
        'last_audio_time': None,
        'is_speaking': False,
        'silence_check_task': None
    }


def ensure_audio_buffer(connection_id: int) -> Dict[str, Any]:
    buffer = audio_buffers.get(connection_id)
    if not buffer:
        buffer = create_audio_buffer()
        audio_buffers[connection_id] = buffer
    return buffer


def initialize_engines():
    """Initialize ASR, LLM, and TTS engines"""
    global asr_engine, llm_engine, tts_engine
    
    try:
        # Initialize ASR
        logger.info("Initializing ASR engine...")
        # Use "tiny" for fastest inference, "base" for better accuracy
        # For GPU: device="cuda", compute_type="float16"
        # For CPU: device="cpu", compute_type="int8" (fastest)
        asr_engine = WhisperASR(model_size="base", device="cpu", compute_type="int8")
        # Don't load model until needed (it's heavy)
        logger.info("ASR engine ready")
        
        # Initialize LLM
        logger.info("Initializing LLM engine...")
        config = load_config()
        # Use phi3:mini for faster responses (10x faster than mistral)
        # Alternative: "llama3:8b-instruct" for better quality but slower
        llm_engine = OllamaLLM(model="phi3:mini")  # Fast model
        llm_engine.load_personality(config)
        logger.info("LLM engine ready")
        
        # Initialize TTS
        logger.info("Initializing TTS engine...")
        tts_engine = PiperTTS()
        logger.info("TTS engine ready")
        
    except Exception as e:
        logger.error(f"Error initializing engines: {e}")
        raise


# Initialize on startup
@app.on_event("startup")
async def startup_event():
    """Initialize engines on startup"""
    initialize_engines()


# Pydantic models
class TextRequest(BaseModel):
    text: str


class ConfigUpdate(BaseModel):
    agent_role: Optional[str] = None
    agent_description: Optional[str] = None
    tone: Optional[str] = None
    language: Optional[str] = None


class WebRTCOffer(BaseModel):
    sdp: str
    type: str
    connection_id: int


class WebRTCIceCandidate(BaseModel):
    session_id: str
    candidate: Optional[str] = None
    sdpMid: Optional[str] = None
    sdpMLineIndex: Optional[int] = None


class WebRTCCloseRequest(BaseModel):
    session_id: str


# API Routes
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Speech-to-Speech API",
        "version": "1.0.0"
    }


@app.get("/config")
async def get_config():
    """Get current agent configuration"""
    return load_config()


@app.post("/config")
async def update_config(config_update: ConfigUpdate):
    """Update agent configuration"""
    config = load_config()
    
    if config_update.agent_role:
        config["agent_role"] = config_update.agent_role
    if config_update.agent_description:
        config["agent_description"] = config_update.agent_description
    if config_update.tone:
        config["tone"] = config_update.tone
    if config_update.language:
        config["language"] = config_update.language
    
    # Save config
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    
    # Reload LLM personality
    if llm_engine:
        llm_engine.load_personality(config)
    
    return {"status": "updated", "config": config}


@app.post("/llm/respond")
async def llm_respond(request: TextRequest):
    """Generate LLM response from text"""
    if not llm_engine:
        raise HTTPException(status_code=500, detail="LLM engine not initialized")
    
    try:
        response = llm_engine.generate_response(request.text)
        return {"response": response}
    except Exception as e:
        logger.error(f"Error generating LLM response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/llm/respond/stream")
async def llm_respond_stream(request: TextRequest):
    """Generate LLM response with streaming"""
    if not llm_engine:
        raise HTTPException(status_code=500, detail="LLM engine not initialized")
    
    def generate():
        try:
            for chunk in llm_engine.generate_response_stream(request.text):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/tts/speak")
async def tts_speak(request: TextRequest):
    """Convert text to speech"""
    if not tts_engine:
        raise HTTPException(status_code=500, detail="TTS engine not initialized")
    
    try:
        logger.info(f"[TTS Test] Testing TTS with text: '{request.text}'")
        audio_data = tts_engine.synthesize(request.text)
        logger.info(f"[TTS Test] ✓ Generated {len(audio_data)} bytes of audio")
        
        # Save to temporary file
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_file.write(audio_data)
        temp_file.close()
        
        logger.info(f"[TTS Test] ✓ Saved audio to: {temp_file.name}")
        
        return FileResponse(
            temp_file.name,
            media_type="audio/wav",
            filename="speech.wav"
        )
    except Exception as e:
        logger.error(f"[TTS Test] ✗ Error in TTS: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tts/test")
async def tts_test():
    """Test TTS with sample data - returns audio info in JSON"""
    if not tts_engine:
        return {"error": "TTS engine not initialized", "status": "error"}
    
    test_text = "Hello, this is a test of the text to speech system."
    logger.info(f"[TTS Test Endpoint] Testing with sample text: '{test_text}'")
    
    try:
        import time
        start_time = time.time()
        
        audio_data = tts_engine.synthesize(test_text)
        
        elapsed_time = time.time() - start_time
        
        # Encode to base64 for logging
        import base64
        audio_b64 = base64.b64encode(audio_data).decode('utf-8')
        
        result = {
            "status": "success",
            "text": test_text,
            "text_length": len(test_text),
            "audio_size_bytes": len(audio_data),
            "audio_base64_length": len(audio_b64),
            "audio_base64_preview": audio_b64[:100] + "..." if len(audio_b64) > 100 else audio_b64,
            "generation_time_seconds": round(elapsed_time, 2),
            "is_valid_wav": audio_data[:4] == b'RIFF' if len(audio_data) >= 4 else False,
            "audio_header": audio_data[:20].hex() if len(audio_data) >= 20 else "too_short",
            "play_url": "/tts/test/play"  # URL to play the audio
        }
        
        logger.info(f"[TTS Test Endpoint] ✓ Test successful: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"[TTS Test Endpoint] ✗ Test failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "text": test_text
        }


@app.get("/tts/test/play")
async def tts_test_play():
    """Test TTS with sample data - returns audio file for playback"""
    if not tts_engine:
        raise HTTPException(status_code=500, detail="TTS engine not initialized")
    
    test_text = "Hello, this is a test of the text to speech system."
    logger.info(f"[TTS Test Play] Generating audio for playback: '{test_text}'")
    
    try:
        audio_data = tts_engine.synthesize(test_text)
        logger.info(f"[TTS Test Play] ✓ Generated {len(audio_data)} bytes of audio")
        
        # Save to temporary file
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_file.write(audio_data)
        temp_file.close()
        
        logger.info(f"[TTS Test Play] ✓ Audio file ready: {temp_file.name}")
        
        return FileResponse(
            temp_file.name,
            media_type="audio/wav",
            filename="tts_test.wav",
            headers={"Content-Disposition": "inline; filename=tts_test.wav"}
        )
    except Exception as e:
        logger.error(f"[TTS Test Play] ✗ Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tts/test/page")
async def tts_test_page():
    """Simple HTML page to test TTS audio playback"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>TTS Audio Test</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
            }
            .test-section {
                margin: 20px 0;
                padding: 20px;
                background: #f9f9f9;
                border-radius: 5px;
            }
            button {
                background: #4CAF50;
                color: white;
                border: none;
                padding: 12px 24px;
                font-size: 16px;
                border-radius: 5px;
                cursor: pointer;
                margin: 5px;
            }
            button:hover {
                background: #45a049;
            }
            button:disabled {
                background: #ccc;
                cursor: not-allowed;
            }
            audio {
                width: 100%;
                margin: 20px 0;
            }
            .info {
                background: #e3f2fd;
                padding: 15px;
                border-radius: 5px;
                margin: 10px 0;
            }
            .error {
                background: #ffebee;
                color: #c62828;
                padding: 15px;
                border-radius: 5px;
                margin: 10px 0;
            }
            input[type="text"] {
                width: 100%;
                padding: 10px;
                font-size: 14px;
                border: 1px solid #ddd;
                border-radius: 5px;
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎙️ TTS Audio Test Page</h1>
            
            <div class="test-section">
                <h2>Test 1: Pre-generated Sample Audio</h2>
                <p>Click the button below to generate and play a test audio:</p>
                <button onclick="playTestAudio()">Generate & Play Test Audio</button>
                <audio id="testAudio" controls style="display: none;"></audio>
                <div id="testInfo" class="info" style="display: none;"></div>
            </div>
            
            <div class="test-section">
                <h2>Test 2: Custom Text</h2>
                <p>Enter your own text to test TTS:</p>
                <input type="text" id="customText" placeholder="Enter text to convert to speech..." value="Hello, this is a custom test message.">
                <button onclick="playCustomAudio()">Generate & Play Custom Audio</button>
                <audio id="customAudio" controls style="display: none;"></audio>
                <div id="customInfo" class="info" style="display: none;"></div>
            </div>
            
            <div class="test-section">
                <h2>Test 3: Check TTS Status</h2>
                <button onclick="checkTTSStatus()">Check TTS Status</button>
                <div id="statusInfo" class="info" style="display: none;"></div>
            </div>
        </div>
        
        <script>
            async function playTestAudio() {
                const audio = document.getElementById('testAudio');
                const info = document.getElementById('testInfo');
                
                info.style.display = 'block';
                info.innerHTML = '⏳ Generating audio...';
                info.className = 'info';
                
                try {
                    // Generate and get audio URL
                    const response = await fetch('/tts/test/play');
                    if (!response.ok) {
                        throw new Error('Failed to generate audio');
                    }
                    
                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);
                    
                    audio.src = url;
                    audio.style.display = 'block';
                    
                    info.innerHTML = `✓ Audio generated successfully!<br>
                        Size: ${(blob.size / 1024).toFixed(2)} KB<br>
                        Type: ${blob.type}<br>
                        <strong>Click play on the audio player above to hear it.</strong>`;
                    info.className = 'info';
                    
                    // Auto-play
                    audio.play().catch(e => {
                        console.error('Auto-play failed:', e);
                        info.innerHTML += '<br><em>Note: Auto-play was blocked. Please click play manually.</em>';
                    });
                } catch (error) {
                    info.innerHTML = `✗ Error: ${error.message}`;
                    info.className = 'error';
                }
            }
            
            async function playCustomAudio() {
                const text = document.getElementById('customText').value;
                if (!text.trim()) {
                    alert('Please enter some text');
                    return;
                }
                
                const audio = document.getElementById('customAudio');
                const info = document.getElementById('customInfo');
                
                info.style.display = 'block';
                info.innerHTML = `⏳ Generating audio for: "${text}"...`;
                info.className = 'info';
                
                try {
                    const response = await fetch('/tts/speak', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ text: text })
                    });
                    
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to generate audio');
                    }
                    
                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);
                    
                    audio.src = url;
                    audio.style.display = 'block';
                    
                    info.innerHTML = `✓ Audio generated successfully!<br>
                        Text: "${text}"<br>
                        Size: ${(blob.size / 1024).toFixed(2)} KB<br>
                        Type: ${blob.type}<br>
                        <strong>Click play on the audio player above to hear it.</strong>`;
                    info.className = 'info';
                    
                    // Auto-play
                    audio.play().catch(e => {
                        console.error('Auto-play failed:', e);
                        info.innerHTML += '<br><em>Note: Auto-play was blocked. Please click play manually.</em>';
                    });
                } catch (error) {
                    info.innerHTML = `✗ Error: ${error.message}`;
                    info.className = 'error';
                }
            }
            
            async function checkTTSStatus() {
                const info = document.getElementById('statusInfo');
                info.style.display = 'block';
                info.innerHTML = '⏳ Checking TTS status...';
                info.className = 'info';
                
                try {
                    const response = await fetch('/tts/test');
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        info.innerHTML = `
                            <strong>✓ TTS is working correctly!</strong><br>
                            Engine: ${data.tts_type || 'pyttsx3'}<br>
                            Test Text: "${data.text}"<br>
                            Audio Size: ${(data.audio_size_bytes / 1024).toFixed(2)} KB<br>
                            Generation Time: ${data.generation_time_seconds}s<br>
                            Valid WAV: ${data.is_valid_wav ? 'Yes ✓' : 'No ✗'}<br>
                            <a href="/tts/test/play" target="_blank">Play Test Audio</a>
                        `;
                        info.className = 'info';
                    } else {
                        info.innerHTML = `✗ TTS Error: ${data.error}`;
                        info.className = 'error';
                    }
                } catch (error) {
                    info.innerHTML = `✗ Error checking status: ${error.message}`;
                    info.className = 'error';
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/webrtc/offer")
async def webrtc_offer(offer: WebRTCOffer):
    websocket = websocket_connections.get(offer.connection_id)
    if not websocket:
        raise HTTPException(status_code=404, detail="WebSocket connection not found")
    
    if asr_engine:
        asr_engine.load_model()
    
    sample_rate = asr_engine.sample_rate if asr_engine else DEFAULT_SAMPLE_RATE
    session = WebRTCAudioSession(
        connection_id=offer.connection_id,
        sample_rate=sample_rate,
        frame_callback=handle_webrtc_pcm,
        on_ended=lambda session_id: webrtc_sessions.pop(session_id, None),
    )
    webrtc_sessions[session.id] = session
    
    rtc_offer = RTCSessionDescription(sdp=offer.sdp, type=offer.type)
    answer = await session.accept_offer(rtc_offer)
    return {
        "sdp": answer.sdp,
        "type": answer.type,
        "session_id": session.id,
    }


@app.post("/webrtc/candidate")
async def webrtc_candidate(candidate: WebRTCIceCandidate):
    session = webrtc_sessions.get(candidate.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="WebRTC session not found")
    
    payload = None
    if candidate.candidate:
        payload = {
            "candidate": candidate.candidate,
            "sdpMid": candidate.sdpMid,
            "sdpMLineIndex": candidate.sdpMLineIndex,
        }
    await session.add_ice_candidate(payload)
    return {"status": "ok"}


@app.post("/webrtc/close")
async def webrtc_close(request: WebRTCCloseRequest):
    session = webrtc_sessions.pop(request.session_id, None)
    if not session:
        return {"status": "ok"}
    await session.close()
    return {"status": "closed"}


def analyze_audio_chunk(audio_b64: str, sample_rate: int) -> Optional[Dict[str, Any]]:
    """
    Decode a base64-encoded chunk, convert it to PCM, and compute RMS energy.
    Returns a dict with PCM bytes (or None) and energy.
    
    The audio data can be:
    1. Raw PCM16 bytes (base64 encoded) - from Django backend
    2. WebM/MP3 format (base64 encoded) - from browser clients
    """
    pcm_data = None
    energy = 0.0
    
    # First, try to decode as raw PCM16 (from Django backend)
    try:
        chunk_bytes = base64.b64decode(audio_b64)
        # Try to interpret as PCM16 int16 samples
        if len(chunk_bytes) >= 2 and len(chunk_bytes) % 2 == 0:
            # Valid PCM16 data (must be even number of bytes)
            samples = np.frombuffer(chunk_bytes, dtype=np.int16)
            if samples.size > 0:
                pcm_data = chunk_bytes
                energy = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
                logger.debug(f"Decoded as PCM16: {len(chunk_bytes)} bytes, {samples.size} samples, energy={energy:.1f}")
    except Exception as e:
        logger.debug(f"Failed to decode as PCM16: {e}")
    
    # If PCM16 decoding failed, try WebM/MP3 conversion (for browser clients)
    if not pcm_data:
        try:
            pcm_data = webm_base64_to_pcm(audio_b64, sample_rate=sample_rate)
            if pcm_data:
                samples = np.frombuffer(pcm_data, dtype=np.int16)
                if samples.size > 0:
                    energy = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
                    logger.debug(f"Converted from WebM/MP3: {len(pcm_data)} bytes PCM, energy={energy:.1f}")
        except AudioConversionError as exc:
            logger.debug(f"Chunk conversion failed for VAD: {exc}")
    
    # If still no PCM data, use raw bytes length as fallback energy estimate
    if not pcm_data:
        try:
            chunk_bytes = base64.b64decode(audio_b64)
            energy = float(len(chunk_bytes))
        except Exception:
            return None
    
    return {
        "pcm": pcm_data,
        "energy": energy,
        "raw": audio_b64,
    }


def analyze_pcm_bytes(pcm_bytes: bytes) -> Optional[Dict[str, Any]]:
    if not pcm_bytes:
        return None
    samples = np.frombuffer(pcm_bytes, dtype=np.int16)
    if samples.size == 0:
        return None
    energy = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
    return {
        "pcm": pcm_bytes,
        "energy": energy,
        "raw": None,
    }


async def process_audio_analysis(
    connection_id: int,
    analysis: Optional[Dict[str, Any]],
    websocket: WebSocket,
) -> None:
    if not analysis:
        return
    
    buffer = ensure_audio_buffer(connection_id)
    pcm_chunk = analysis.get("pcm")
    raw_chunk = analysis.get("raw")
    energy = analysis.get("energy", 0.0)
    
    # Update noise floor
    noise_floor = buffer.get('noise_floor')
    if noise_floor is None:
        noise_floor = energy
    buffer['noise_floor'] = noise_floor
    
    dynamic_threshold = max(MIN_SPEECH_ENERGY, noise_floor + ENERGY_MARGIN)
    has_pcm = pcm_chunk is not None
    has_speech = has_pcm and (energy >= dynamic_threshold)
    current_time = time.time()
    
    # Only log when speaking state actually changes (not every chunk)
    was_speaking_state = buffer.get('was_speaking_state', False)  # Track previous has_speech value
    log_counter = buffer.get('log_counter', 0)
    buffer['log_counter'] = log_counter + 1
    
    # Check if state actually changed
    state_changed = (has_speech != was_speaking_state)
    if state_changed:
        buffer['was_speaking_state'] = has_speech  # Update tracked state
    
    # Only log on actual state change or every 500 chunks (much less frequent)
    if state_changed or log_counter % 500 == 0:
        if state_changed:
            logger.debug(
                f"VAD state changed: energy={energy:.1f}, threshold={dynamic_threshold:.1f}, "
                f"noise_floor={noise_floor:.1f}, speaking={has_speech} (was {was_speaking_state})"
            )
        # Periodic log every 500 chunks (very infrequent)
        elif log_counter % 500 == 0:
            logger.debug(
                f"VAD periodic: energy={energy:.1f}, threshold={dynamic_threshold:.1f}, "
                f"noise_floor={noise_floor:.1f}, speaking={has_speech}"
            )
    
    chunk_entry = {
        "timestamp": current_time,
    }
    if raw_chunk is not None:
        chunk_entry["b64"] = raw_chunk
    if pcm_chunk:
        chunk_entry["pcm"] = pcm_chunk
    
    if has_speech:
        pre_buffer = buffer.get('pre_speech_buffer', [])
        chunks_to_add = pre_buffer + [chunk_entry] if pre_buffer else [chunk_entry]
        pre_buffer.clear()
        
        for entry in chunks_to_add:
            if entry.get('b64') is not None:
                buffer['chunks'].append(entry['b64'])
            if entry.get('pcm'):
                buffer['pcm_chunks'].append(entry['pcm'])
            buffer['chunk_timestamps'].append(entry['timestamp'])
            buffer['speech_chunk_times'].append(entry['timestamp'])
        
        # Retain only recent speech timestamps (5s window)
        cutoff_time = current_time - 5.0
        buffer['speech_chunk_times'] = [
            t for t in buffer['speech_chunk_times'] if t > cutoff_time
        ]
        
        # Enforce max buffer duration for stored chunks
        cutoff_time = current_time - max_buffer_duration
        while buffer['chunk_timestamps'] and buffer['chunk_timestamps'][0] < cutoff_time:
            buffer['chunk_timestamps'].pop(0)
            if buffer['chunks']:
                buffer['chunks'].pop(0)
            if buffer['pcm_chunks']:
                buffer['pcm_chunks'].pop(0)
        
        speech_in_last_second = len([
            t for t in buffer['speech_chunk_times'] if current_time - t < 1.0
        ])
        speech_in_last_half_second = len([
            t for t in buffer['speech_chunk_times'] if current_time - t < 0.5
        ])
        
        has_sustained_speech = (
            speech_in_last_half_second >= 2 or speech_in_last_second >= 3
        )
        has_recent_speech = speech_in_last_half_second > 0
        
        if has_sustained_speech or (buffer['is_speaking'] and has_recent_speech):
            buffer['last_audio_time'] = current_time
        
        if not buffer['is_speaking'] and has_sustained_speech:
            buffer['is_speaking'] = True
            logger.info(
                "User started speaking (energy-based VAD), starting silence detection"
            )
            try:
                await websocket.send_json({
                    "type": "call_status",
                    "status": "speaking"
                })
            except Exception as exc:
                logger.error(f"Error sending speaking status: {exc}")
            task = buffer.get('silence_check_task')
            if not task or task.done():
                buffer['silence_check_task'] = asyncio.create_task(
                    check_silence_periodically(websocket, connection_id)
                )
    else:
        # Move noise floor slowly towards observed energy
        buffer['noise_floor'] = (noise_floor * 0.9) + (energy * 0.1)
        if buffer['is_speaking']:
            # Keep trailing silence to avoid cutting words
            if raw_chunk is not None:
                buffer['chunks'].append(raw_chunk)
            if pcm_chunk:
                buffer['pcm_chunks'].append(pcm_chunk)
            buffer['chunk_timestamps'].append(current_time)
        else:
            # Store short pre-roll before speech starts
            if raw_chunk is not None or pcm_chunk:
                pre_buffer = buffer.get('pre_speech_buffer', [])
                pre_buffer.append(chunk_entry)
                if len(pre_buffer) > PRE_ROLL_CHUNKS:
                    pre_buffer.pop(0)


async def handle_webrtc_pcm(connection_id: int, pcm_bytes: bytes, sample_rate: int) -> None:
    _ = sample_rate  # Sample rate is currently fixed but kept for future adjustments
    websocket = websocket_connections.get(connection_id)
    if not websocket:
        logger.warning(
            "Ignoring WebRTC audio for unknown websocket connection %s",
            connection_id,
        )
        return
    
    analysis = analyze_pcm_bytes(pcm_bytes)
    await process_audio_analysis(connection_id, analysis, websocket)


async def process_audio_buffer(websocket: WebSocket, connection_id: int):
    """Process accumulated audio chunks when silence is detected"""
    # Ensure we're using the current websocket from connections dict
    current_ws = websocket_connections.get(connection_id)
    if not current_ws:
        logger.warning(f"No WebSocket found for connection {connection_id}")
        return
    # Use the current websocket (in case it was reconnected)
    websocket = current_ws
    
    buffer = audio_buffers.get(connection_id)
    if not buffer:
        logger.warning(f"No buffer found for connection {connection_id}")
        return
    
    has_webm_chunks = bool(buffer['chunks'])
    has_pcm_chunks = bool(buffer.get('pcm_chunks'))
    
    if not has_webm_chunks and not has_pcm_chunks:
        logger.warning("No audio chunks to process")
        return
    
    if has_pcm_chunks:
        num_chunks = len(buffer.get('pcm_chunks', []))
    else:
        num_chunks = len(buffer['chunks'])
    logger.info(f"Processing audio buffer: {num_chunks} chunks")
    
    try:
        sample_rate = asr_engine.sample_rate if asr_engine else DEFAULT_SAMPLE_RATE
        pcm_chunks = buffer.get('pcm_chunks', [])
        
        if pcm_chunks:
            pcm_audio = b"".join(pcm_chunks)
            logger.info(f"Converted to PCM: {len(pcm_audio)} bytes from cached PCM chunks ({len(pcm_chunks)} segments)")
        else:
            logger.info("PCM cache empty, converting stored WebM chunks")
            try:
                pcm_audio = webm_chunks_to_pcm(
                    buffer['chunks'],
                    sample_rate=sample_rate
                )
            except Exception as e:
                logger.error(f"Error converting audio chunks to PCM: {e}")
                # Fallback: try with just the last chunk
                if buffer['chunks']:
                    logger.info("Trying fallback: processing last chunk only")
                    try:
                        pcm_audio = webm_base64_to_pcm(
                            buffer['chunks'][-1],
                            sample_rate=sample_rate
                        )
                    except Exception as e2:
                        logger.error(f"Fallback also failed: {e2}")
                        raise
                else:
                    raise
        
        if not pcm_audio:
            logger.warning("PCM audio is empty after conversion")
            await websocket.send_json({
                "type": "error",
                "message": "No speech detected in audio."
            })
            await websocket.send_json({
                "type": "call_status",
                "status": "listening"
            })
            buffer['chunks'] = []
            buffer['pcm_chunks'] = []
            buffer['chunk_timestamps'] = []
            buffer['speech_chunk_times'] = []
            buffer['pre_speech_buffer'] = []
            buffer['noise_floor'] = None
            buffer['last_audio_time'] = None
            buffer['is_speaking'] = False
            return
        
        logger.info(f"Converted to PCM: {len(pcm_audio)} bytes ready for transcription")
        
        # Transcribe
        transcript = asr_engine.transcribe_audio(pcm_audio) if asr_engine else ""
        
        if transcript:
            logger.info(f"Transcription result: '{transcript}'")
            try:
                # Always get fresh WebSocket from connections dict
                current_ws = websocket_connections.get(connection_id)
                if not current_ws:
                    logger.error(f"WebSocket connection {connection_id} not found when sending transcription!")
                    return
                
                await current_ws.send_json({
                    "type": "transcription",
                    "text": transcript
                })
                logger.info(f"✓ Sent transcription to frontend: '{transcript}' (connection_id: {connection_id})")
                
            except Exception as e:
                logger.error(f"Error sending transcription: {e}", exc_info=True)
                return
            
            try:
                logger.info(f"Calling handle_user_text with: '{transcript}' (connection_id: {connection_id})")
                # Use the current websocket from connections dict
                await handle_user_text(current_ws, transcript)
                logger.info("handle_user_text completed successfully")
            except Exception as e:
                logger.error(f"Error in handle_user_text: {e}", exc_info=True)
        else:
            logger.warning("No speech detected in audio buffer")
            await websocket.send_json({
                "type": "error",
                "message": "No speech detected in audio."
            })
            # Still go back to listening
            await websocket.send_json({
                "type": "call_status",
                "status": "listening"
            })
        
        # Clear buffer
        buffer['chunks'] = []
        buffer['pcm_chunks'] = []
        buffer['chunk_timestamps'] = []
        buffer['speech_chunk_times'] = []
        buffer['pre_speech_buffer'] = []
        buffer['noise_floor'] = None
        buffer['last_audio_time'] = None
        buffer['is_speaking'] = False
        
    except Exception as e:
        logger.error(f"Error processing audio buffer: {e}", exc_info=True)
        await websocket.send_json({
            "type": "error",
            "message": f"Error processing audio: {str(e)}"
        })
        # Clear buffer on error
        buffer['chunks'] = []
        buffer['pcm_chunks'] = []
        buffer['chunk_timestamps'] = []
        buffer['speech_chunk_times'] = []
        buffer['pre_speech_buffer'] = []
        buffer['noise_floor'] = None
        buffer['last_audio_time'] = None
        buffer['is_speaking'] = False


async def check_silence_periodically(websocket: WebSocket, connection_id: int):
    """Background task to check for silence and process audio"""
    buffer = audio_buffers.get(connection_id)
    if not buffer:
        logger.warning(f"No buffer found for connection {connection_id}")
        return
    
    logger.info(f"Starting silence detection for connection {connection_id}")
    
    try:
        while buffer.get('is_speaking', False):
            await asyncio.sleep(0.5)  # Check every 500ms
            
            if not buffer.get('last_audio_time'):
                continue
            
            current_time = time.time()
            silence_duration = current_time - buffer['last_audio_time']
            
            logger.debug(f"Silence check: duration={silence_duration:.2f}s, chunks={len(buffer.get('chunks', []))}")
            
            # Send silence duration update to frontend
            try:
                await websocket.send_json({
                    "type": "call_status",
                    "status": "speaking",
                    "silence_duration": int(silence_duration * 1000)  # in milliseconds
                })
            except Exception as e:
                logger.error(f"Error sending status update: {e}")
                break
            
            if silence_duration >= silence_threshold:
                logger.info(f"Silence detected ({silence_duration:.2f}s), processing {len(buffer.get('chunks', []))} chunks...")
                try:
                    await websocket.send_json({
                        "type": "call_status",
                        "status": "processing"
                    })
                    await process_audio_buffer(websocket, connection_id)
                    # After processing, go back to listening
                    await websocket.send_json({
                        "type": "call_status",
                        "status": "listening"
                    })
                except Exception as e:
                    logger.error(f"Error processing audio buffer: {e}")
                break
    except asyncio.CancelledError:
        logger.info(f"Silence detection task cancelled for connection {connection_id}")
    except Exception as e:
        logger.error(f"Error in silence detection: {e}")


async def generate_and_send_tts_sentence(connection_id: int, sentence: str, sentence_num: int) -> None:
    """
    Generate TTS for a single sentence and send it to the frontend immediately.
    This allows audio to start playing while the LLM is still generating.
    """
    try:
        current_ws = websocket_connections.get(connection_id)
        if not current_ws or current_ws.client_state.name != "CONNECTED":
            logger.warning(f"[TTS] WebSocket not connected for sentence {sentence_num}, skipping")
            return
        
        logger.info(f"[TTS] Generating TTS for sentence {sentence_num}: '{sentence[:50]}...'")
        loop = asyncio.get_event_loop()
        
        # Calculate timeout for this sentence
        sentence_timeout = max(30.0, min(90.0, len(sentence) * 0.2))
        
        try:
            start_time = time.time()
            sentence_audio = await asyncio.wait_for(
                loop.run_in_executor(None, tts_engine.synthesize, sentence),
                timeout=sentence_timeout
            )
            elapsed_time = time.time() - start_time
            
            if len(sentence_audio) == 0:
                logger.error(f"[TTS] Sentence {sentence_num} generated empty audio")
                return
            
            logger.info(f"[TTS] ✓ Sentence {sentence_num} generated: {len(sentence_audio)} bytes in {elapsed_time:.2f}s")
            
            # Encode and send immediately
            audio_b64 = base64.b64encode(sentence_audio).decode('utf-8')
            
            # Verify connection is still valid
            current_ws = websocket_connections.get(connection_id)
            if not current_ws or current_ws.client_state.name != "CONNECTED":
                logger.warning(f"[TTS] WebSocket disconnected before sending sentence {sentence_num}")
                return
            
            await current_ws.send_json({
                "type": "audio_output",
                "audio": audio_b64,
                "format": "wav",
                "sentence_num": sentence_num,
                "is_streaming": True
            })
            
            logger.info(f"[TTS] ✓ Sent sentence {sentence_num} audio to frontend ({len(audio_b64)} chars)")
            
        except asyncio.TimeoutError:
            logger.error(f"[TTS] ✗ Sentence {sentence_num} timed out after {sentence_timeout:.1f}s")
        except Exception as e:
            logger.error(f"[TTS] ✗ Error generating sentence {sentence_num}: {e}", exc_info=True)
            
    except Exception as e:
        logger.error(f"[TTS] ✗ Error in generate_and_send_tts_sentence: {e}", exc_info=True)


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences using regex.
    Handles periods, exclamation marks, and question marks.
    """
    # Pattern: sentence ending (. ! ?) followed by space or end of string
    # This handles most cases but may need refinement for edge cases
    sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])$'
    sentences = re.split(sentence_pattern, text.strip())
    # Filter out empty strings and strip whitespace
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


def concatenate_wav_files(wav_data_list: List[bytes]) -> bytes:
    """
    Concatenate multiple WAV files into one.
    Assumes all WAV files have the same sample rate, channels, and bit depth.
    
    Args:
        wav_data_list: List of WAV file data (bytes)
        
    Returns:
        bytes: Combined WAV file data
    """
    if not wav_data_list:
        raise ValueError("No WAV files to concatenate")
    
    if len(wav_data_list) == 1:
        return wav_data_list[0]
    
    # Parse first WAV to get format info
    first_wav = wav_data_list[0]
    if len(first_wav) < 44:
        raise ValueError("Invalid WAV file: too short")
    
    # Extract format info from first WAV
    channels = struct.unpack('<H', first_wav[22:24])[0]
    sample_rate = struct.unpack('<I', first_wav[24:28])[0]
    bits_per_sample = struct.unpack('<H', first_wav[34:36])[0]
    block_align = struct.unpack('<H', first_wav[32:34])[0]
    
    logger.info(f"[TTS] WAV format: {channels} channels, {sample_rate} Hz, {bits_per_sample} bits")
    
    # Extract PCM data from all WAV files
    all_pcm_data = []
    
    for i, wav_data in enumerate(wav_data_list):
        if len(wav_data) < 44:
            logger.warning(f"[TTS] Skipping invalid WAV file {i+1}")
            continue
        
        # Find "data" chunk
        data_start = 36
        while data_start < len(wav_data) - 8:
            chunk_id = wav_data[data_start:data_start+4]
            chunk_size = struct.unpack('<I', wav_data[data_start+4:data_start+8])[0]
            
            if chunk_id == b'data':
                pcm_data = wav_data[data_start+8:data_start+8+chunk_size]
                all_pcm_data.append(pcm_data)
                logger.info(f"[TTS] Extracted {len(pcm_data)} bytes from WAV {i+1}")
                break
            
            data_start += 8 + chunk_size
        else:
            logger.warning(f"[TTS] Could not find data chunk in WAV {i+1}")
    
    if not all_pcm_data:
        raise ValueError("No valid PCM data extracted from WAV files")
    
    # Combine all PCM data
    combined_pcm = b''.join(all_pcm_data)
    total_data_size = len(combined_pcm)
    
    # Create new WAV file
    # RIFF header
    riff_size = 36 + total_data_size  # 36 = 4 (WAVE) + 8 (fmt chunk header) + 16 (fmt data) + 8 (data chunk header)
    wav_file = io.BytesIO()
    wav_file.write(b'RIFF')
    wav_file.write(struct.pack('<I', riff_size))
    wav_file.write(b'WAVE')
    
    # fmt chunk
    wav_file.write(b'fmt ')
    wav_file.write(struct.pack('<I', 16))  # fmt chunk size
    wav_file.write(struct.pack('<H', 1))   # PCM format
    wav_file.write(struct.pack('<H', channels))
    wav_file.write(struct.pack('<I', sample_rate))
    wav_file.write(struct.pack('<I', sample_rate * channels * bits_per_sample // 8))  # byte rate
    wav_file.write(struct.pack('<H', block_align))
    wav_file.write(struct.pack('<H', bits_per_sample))
    
    # data chunk
    wav_file.write(b'data')
    wav_file.write(struct.pack('<I', total_data_size))
    wav_file.write(combined_pcm)
    
    result = wav_file.getvalue()
    logger.info(f"[TTS] Concatenated {len(wav_data_list)} WAV files into {len(result)} bytes")
    return result


async def handle_user_text(websocket: WebSocket, user_text: str):
    """Generate LLM + TTS response for provided user text."""
    connection_id = id(websocket)
    logger.info(f"handle_user_text called with text: '{user_text}' (connection_id: {connection_id})")
    
    # Verify WebSocket is still in our connections dict and get the current instance
    if connection_id not in websocket_connections:
        logger.error(f"WebSocket connection {connection_id} not found in websocket_connections dict!")
        return
    
    # Use the WebSocket from connections dict to ensure we have the correct/current instance
    websocket = websocket_connections[connection_id]
    
    if websocket.client_state.name != "CONNECTED":
        logger.error(f"WebSocket {connection_id} not connected, state: {websocket.client_state.name}")
        return
    
    if not user_text.strip():
        logger.warning("handle_user_text called with empty text")
        return
    
    if not llm_engine:
        logger.error("LLM engine not initialized")
        await websocket.send_json({
            "type": "error",
            "message": "LLM engine not initialized"
        })
        return
    if not tts_engine:
        logger.error("TTS engine not initialized")
        await websocket.send_json({
            "type": "error",
            "message": "TTS engine not initialized"
        })
        return
    
    # Stream the LLM response and start TTS generation early for faster response
    full_response = ""
    logger.info(f"Generating LLM response for: '{user_text}'")
    chunk_count = 0
    
    # Track sentences for streaming TTS
    accumulated_text = ""
    processed_sentences = []
    tts_tasks = []  # Store async TTS tasks
    use_streaming_tts = False  # Flag to determine if we used streaming
    
    # Send TTS status
    current_ws = websocket_connections.get(connection_id)
    if current_ws and current_ws.client_state.name == "CONNECTED":
        try:
            await current_ws.send_json({
                "type": "tts_status",
                "status": "waiting",
                "message": "Waiting for response..."
            })
        except Exception:
            pass
    
    try:
        for chunk in llm_engine.generate_response_stream(user_text):
            if not chunk:
                continue
            full_response += chunk
            accumulated_text += chunk
            chunk_count += 1
            
            # Truncate if response gets too long (safety measure)
            MAX_RESPONSE_LENGTH = 200  # Maximum characters for response
            if len(full_response) > MAX_RESPONSE_LENGTH:
                # Find the last sentence end before the limit
                truncated = full_response[:MAX_RESPONSE_LENGTH]
                last_period = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?'))
                if last_period > MAX_RESPONSE_LENGTH * 0.7:  # Only truncate if we have a good sentence break
                    full_response = truncated[:last_period + 1]
                    logger.info(f"[LLM] Response truncated to {len(full_response)} chars (max: {MAX_RESPONSE_LENGTH})")
                    break
            try:
                # Always get fresh WebSocket from connections dict
                current_ws = websocket_connections.get(connection_id)
                if not current_ws:
                    logger.error(f"WebSocket connection {connection_id} lost during streaming (chunk {chunk_count})")
                    break
                
                # Check WebSocket state before sending
                if current_ws.client_state.name != "CONNECTED":
                    logger.error(f"WebSocket disconnected during streaming (chunk {chunk_count}), state: {current_ws.client_state.name}")
                    break
                    
                await current_ws.send_json({
                    "type": "llm_stream_chunk",
                    "text": chunk
                })
                if chunk_count <= 3 or chunk_count % 10 == 0:  # Log first 3 and every 10th
                    logger.debug(f"Sent LLM chunk {chunk_count}: '{chunk[:50]}...' (connection_id: {connection_id})")
                
                # DISABLED: Streaming TTS temporarily - causes audio cutting issues
                # Will re-enable after proper audio queue implementation
                # Check for complete sentences and start TTS generation early
                # sentences = split_into_sentences(accumulated_text)
                # if len(sentences) > len(processed_sentences):
                #     # We have new complete sentences
                #     new_sentences = sentences[len(processed_sentences):]
                #     logger.info(f"[TTS] Found {len(new_sentences)} new complete sentence(s), starting TTS generation")
                #     
                #     # Start TTS generation for new sentences in parallel
                #     loop = asyncio.get_event_loop()
                #     for sentence in new_sentences:
                #         if len(sentence.strip()) >= 20:  # Only process meaningful sentences
                #             processed_sentences.append(sentence)
                #             use_streaming_tts = True
                #             # Start TTS generation in background
                #             task = asyncio.create_task(
                #                 generate_and_send_tts_sentence(connection_id, sentence, len(processed_sentences))
                #             )
                #             tts_tasks.append(task)
                #             logger.info(f"[TTS] Started TTS task for sentence {len(processed_sentences)}: '{sentence[:50]}...'")
                        
            except WebSocketDisconnect:
                logger.error(f"WebSocket disconnected while sending chunk {chunk_count}")
                break
            except Exception as e:
                logger.error(f"Error sending LLM chunk {chunk_count}: {e}", exc_info=True)
                break
    except Exception as e:
        logger.error(f"Error generating LLM response: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"LLM error: {str(e)}"
            })
        except Exception as send_err:
            logger.error(f"Error sending error message: {send_err}")
        return

    if not full_response:
        logger.warning("LLM returned an empty response")
        await websocket.send_json({
            "type": "error",
            "message": "LLM returned an empty response."
        })
        return

    logger.info(f"[LLM] ===== SENDING FINAL LLM RESPONSE =====")
    logger.info(f"[LLM] Response length: {len(full_response)} characters")
    logger.info(f"[LLM] Number of chunks sent: {chunk_count}")
    logger.info(f"[LLM] Full response text: '{full_response}'")
    logger.info(f"[LLM] Response preview: '{full_response[:100]}...'")
    
    # Always get fresh WebSocket from connections dict to ensure we have the current connection
    current_ws = websocket_connections.get(connection_id)
    if not current_ws:
        logger.error(f"WebSocket connection {connection_id} not found in websocket_connections dict!")
        return
    
    # Check WebSocket state and send response
    try:
        # Check if WebSocket is still connected
        ws_state = current_ws.client_state.name
        logger.info(f"WebSocket state before sending llm_response: {ws_state} (connection_id: {connection_id})")
        
        if ws_state != "CONNECTED":
            logger.error(f"WebSocket not connected, state: {ws_state}")
            return
        
        response_msg = {
            "type": "llm_response",
            "text": full_response,
            "user_text": user_text
        }
        logger.info(f"Sending llm_response message (text length: {len(full_response)}, connection_id: {connection_id})")
        
        # Send the response
        await current_ws.send_json(response_msg)
        logger.info(f"✓ Successfully sent llm_response to frontend (connection_id: {connection_id}, state: {current_ws.client_state.name})")
        logger.info(f"✓ llm_response message content preview: text_length={len(full_response)}, user_text='{user_text[:50]}...'")
        
        # Send a simple verification message immediately after
        try:
            await current_ws.send_json({
                "type": "llm_response_sent",
                "message": "LLM response was sent successfully",
                "text_length": len(full_response)
            })
            logger.info(f"✓ Sent verification message after llm_response")
        except Exception as verify_err:
            logger.warning(f"Failed to send verification message: {verify_err}")
        
        # Verify it was sent by checking state again
        if current_ws.client_state.name != "CONNECTED":
            logger.warning(f"WebSocket state changed after send: {current_ws.client_state.name}")
            
    except WebSocketDisconnect as e:
        logger.error(f"WebSocket disconnected while sending llm_response: {e}")
        return
    except Exception as e:
        logger.error(f"Error sending final LLM response: {e}", exc_info=True)
        # Try to send error message to user
        try:
            current_ws = websocket_connections.get(connection_id)
            if current_ws and current_ws.client_state.name == "CONNECTED":
                await current_ws.send_json({
                    "type": "error",
                    "message": f"Failed to send response: {str(e)}"
                })
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")
    
    # If we started streaming TTS, wait for all tasks to complete
    # Otherwise, generate TTS for the full response
    if use_streaming_tts and tts_tasks:
        logger.info(f"[TTS] Waiting for {len(tts_tasks)} streaming TTS tasks to complete...")
        try:
            # Wait for all TTS tasks with a timeout
            await asyncio.wait_for(asyncio.gather(*tts_tasks, return_exceptions=True), timeout=300.0)
            logger.info(f"[TTS] All streaming TTS tasks completed")
        except asyncio.TimeoutError:
            logger.warning(f"[TTS] Some TTS tasks timed out, but continuing...")
        except Exception as e:
            logger.error(f"[TTS] Error waiting for TTS tasks: {e}", exc_info=True)
        
        # Send completion status
        current_ws = websocket_connections.get(connection_id)
        if current_ws and current_ws.client_state.name == "CONNECTED":
            try:
                await current_ws.send_json({
                    "type": "tts_status",
                    "status": "complete",
                    "message": "Audio generation complete"
                })
            except Exception:
                pass
        return  # Streaming TTS is done, no need for full response TTS
    
    # Generate TTS - balance speed and reliability (fallback if streaming didn't start)
    # pyttsx3 is slow, so split more aggressively to avoid timeouts
    SHORT_RESPONSE_THRESHOLD = 150  # Lower threshold - pyttsx3 is slow, split earlier
    logger.info(f"[TTS] ===== STARTING TTS GENERATION =====")
    logger.info(f"[TTS] Full response text: '{full_response}'")
    logger.info(f"[TTS] Response length: {len(full_response)} characters")
    tts_start_time = time.time()
    
    try:
        # Get current WebSocket connection
        logger.info(f"[TTS] Getting WebSocket connection for connection_id: {connection_id}")
        current_ws = websocket_connections.get(connection_id)
        if not current_ws:
            logger.error(f"[TTS] ✗ WebSocket connection {connection_id} not found for TTS!")
            logger.error(f"[TTS] Available connections: {list(websocket_connections.keys())}")
            return
        
        logger.info(f"[TTS] ✓ WebSocket connection found")
        ws_state = current_ws.client_state.name
        logger.info(f"[TTS] WebSocket state: {ws_state}")
        
        if ws_state != "CONNECTED":
            logger.error(f"[TTS] ✗ WebSocket {connection_id} not connected for TTS, state: {ws_state}")
            return
        
        logger.info(f"[TTS] ✓ WebSocket is CONNECTED, proceeding with TTS generation")
        
        # Send status update to frontend that TTS generation has started
        try:
            await current_ws.send_json({
                "type": "tts_status",
                "status": "generating",
                "message": "Generating audio..."
            })
            logger.info(f"[TTS] ✓ Sent TTS status: generating")
        except Exception as status_err:
            logger.warning(f"[TTS] Failed to send TTS status update: {status_err}")
        
        loop = asyncio.get_event_loop()
        final_audio_data = None
        
        # If response is short, generate as one piece
        if len(full_response) <= SHORT_RESPONSE_THRESHOLD:
            logger.info(f"[TTS] Response is short ({len(full_response)} chars), generating as single piece")
            
            # Calculate timeout for full response - pyttsx3 is VERY slow, be very generous
            # pyttsx3 can take 0.5-1 second per character in worst case
            timeout = max(120.0, min(300.0, len(full_response) * 0.8))  # Much more generous: 120s min, 0.8s per char
            logger.info(f"[TTS] Using timeout: {timeout:.1f}s for {len(full_response)} chars (pyttsx3 is slow)")
            
            try:
                start_time = time.time()
                final_audio_data = await asyncio.wait_for(
                    loop.run_in_executor(None, tts_engine.synthesize, full_response),
                    timeout=timeout
                )
                elapsed_time = time.time() - start_time
                logger.info(f"[TTS] ✓ TTS generated: {len(final_audio_data)} bytes in {elapsed_time:.2f}s")
            except asyncio.TimeoutError:
                logger.error(f"[TTS] ✗ TTS timed out after {timeout:.1f}s")
                raise
        else:
            # For long responses, split into sentences, generate each, then concatenate
            logger.info(f"[TTS] Response is long ({len(full_response)} chars), splitting into sentences")
            sentences = split_into_sentences(full_response)
            logger.info(f"[TTS] Split into {len(sentences)} sentences")
            
            # Generate TTS for each sentence
            sentence_audio_list = []
            total_generation_time = 0.0
            failed_sentences = []
            
            for sentence_idx, sentence in enumerate(sentences, 1):
                if not sentence.strip():
                    continue
                
                logger.info(f"[TTS] Processing sentence {sentence_idx}/{len(sentences)}: '{sentence[:50]}...'")
                logger.info(f"[TTS] Full sentence text: '{sentence}'")
                
                # Calculate timeout per sentence - be generous to avoid timeouts
                sentence_timeout = max(30.0, min(90.0, len(sentence) * 0.2))  # Increased min from 20 to 30, max from 45 to 90, multiplier from 0.15 to 0.2
                logger.info(f"[TTS] Using timeout: {sentence_timeout:.1f}s for sentence {sentence_idx} ({len(sentence)} chars)")
                
                try:
                    start_time = time.time()
                    sentence_audio = await asyncio.wait_for(
                        loop.run_in_executor(None, tts_engine.synthesize, sentence),
                        timeout=sentence_timeout
                    )
                    elapsed_time = time.time() - start_time
                    total_generation_time += elapsed_time
                    
                    if len(sentence_audio) == 0:
                        logger.error(f"[TTS] ✗ Sentence {sentence_idx} generated empty audio!")
                        failed_sentences.append((sentence_idx, "Empty audio"))
                        continue
                    
                    sentence_audio_list.append(sentence_audio)
                    logger.info(f"[TTS] ✓ Sentence {sentence_idx} generated: {len(sentence_audio)} bytes in {elapsed_time:.2f}s")
                    
                except asyncio.TimeoutError:
                    logger.error(f"[TTS] ✗ Sentence {sentence_idx} timed out after {sentence_timeout:.1f}s")
                    logger.error(f"[TTS] Sentence text: '{sentence}'")
                    failed_sentences.append((sentence_idx, f"Timeout after {sentence_timeout:.1f}s"))
                    continue
                except Exception as e:
                    logger.error(f"[TTS] ✗ Error generating sentence {sentence_idx}: {e}", exc_info=True)
                    failed_sentences.append((sentence_idx, str(e)))
                    continue
            
            # If no sentences succeeded, try fallback: generate entire response as one piece
            if not sentence_audio_list:
                logger.warning(f"[TTS] ✗✗✗ ALL SENTENCES FAILED ✗✗✗")
                logger.warning(f"[TTS] Failed sentences: {failed_sentences}")
                logger.warning(f"[TTS] Attempting fallback: generating entire response as one piece...")
                
                # Fallback: try generating the whole response, even if it's long
                fallback_timeout = max(180.0, min(360.0, len(full_response) * 0.25))  # Very generous timeout for fallback
                logger.info(f"[TTS] Using fallback timeout: {fallback_timeout:.1f}s for full response ({len(full_response)} chars)")
                
                try:
                    start_time = time.time()
                    final_audio_data = await asyncio.wait_for(
                        loop.run_in_executor(None, tts_engine.synthesize, full_response),
                        timeout=fallback_timeout
                    )
                    elapsed_time = time.time() - start_time
                    logger.info(f"[TTS] ✓ Fallback TTS generated: {len(final_audio_data)} bytes in {elapsed_time:.2f}s")
                    
                    if len(final_audio_data) == 0:
                        raise ValueError("Fallback TTS generated empty audio")
                    
                    # Skip to sending (final_audio_data is already set)
                except asyncio.TimeoutError:
                    logger.error(f"[TTS] ✗ Fallback TTS also timed out after {fallback_timeout:.1f}s")
                    raise ValueError(f"TTS generation failed: All sentences failed and fallback timed out. Failed sentences: {failed_sentences}")
                except Exception as e:
                    logger.error(f"[TTS] ✗ Fallback TTS also failed: {e}", exc_info=True)
                    raise ValueError(f"TTS generation failed: All sentences failed and fallback failed. Failed sentences: {failed_sentences}, Fallback error: {str(e)}")
            else:
                # Some sentences succeeded, concatenate them
                logger.info(f"[TTS] Successfully generated {len(sentence_audio_list)}/{len(sentences)} sentences")
                if failed_sentences:
                    logger.warning(f"[TTS] Some sentences failed: {failed_sentences}")
                
                # Concatenate all sentence audio into one WAV file
                logger.info(f"[TTS] Concatenating {len(sentence_audio_list)} audio chunks...")
                logger.info(f"[TTS] Total audio bytes before concatenation: {sum(len(a) for a in sentence_audio_list)}")
                try:
                    final_audio_data = concatenate_wav_files(sentence_audio_list)
                    logger.info(f"[TTS] ✓ Concatenated audio: {len(final_audio_data)} bytes")
                    logger.info(f"[TTS] Total generation time: {total_generation_time:.2f} seconds")
                    
                    # Verify concatenated audio is valid
                    if len(final_audio_data) < 44:
                        raise ValueError(f"Concatenated audio too short: {len(final_audio_data)} bytes")
                    if final_audio_data[:4] != b'RIFF':
                        raise ValueError("Concatenated audio missing RIFF header")
                    logger.info(f"[TTS] ✓ Concatenated audio verified as valid WAV")
                except Exception as concat_err:
                    logger.error(f"[TTS] ✗ Error concatenating audio: {concat_err}", exc_info=True)
                    raise ValueError(f"Failed to concatenate audio: {str(concat_err)}")
        
        # Verify final audio
        if not final_audio_data or len(final_audio_data) == 0:
            raise ValueError("Generated audio data is empty")
        
        # Verify connection is still valid
        current_ws = websocket_connections.get(connection_id)
        if not current_ws:
            logger.warning(f"[TTS] WebSocket {connection_id} not found in connections (may have disconnected)")
            return
        if current_ws.client_state.name != "CONNECTED":
            logger.warning(f"[TTS] WebSocket {connection_id} state is {current_ws.client_state.name} (not CONNECTED), but continuing to send audio")
            # Continue anyway - the connection might still be valid for sending
        
        # Encode and send complete audio
        logger.info(f"[TTS] Encoding and sending complete audio ({len(final_audio_data)} bytes)...")
        audio_b64 = base64.b64encode(final_audio_data).decode('utf-8')
        logger.info(f"[TTS] Base64 encoded audio length: {len(audio_b64)} characters")
        
        # Verify WebSocket is still connected before sending
        # Re-check connection right before sending (it might have disconnected during TTS generation)
        current_ws = websocket_connections.get(connection_id)
        if not current_ws:
            logger.error(f"[TTS] ✗ WebSocket connection {connection_id} not found in connections dict")
            return
        if current_ws.client_state.name != "CONNECTED":
            logger.error(f"[TTS] ✗ WebSocket disconnected before sending audio! State: {current_ws.client_state.name}")
            return
        
        logger.info(f"[TTS] Sending audio_output message to frontend...")
        try:
            await current_ws.send_json({
                "type": "audio_output",
                "audio": audio_b64,
                "format": "wav"
            })
        except Exception as send_error:
            logger.error(f"[TTS] ✗ Failed to send audio_output: {send_error}", exc_info=True)
            # Don't raise - just log the error, connection might have closed
            return
        
        total_tts_time = time.time() - tts_start_time
        logger.info(f"[TTS] ✓✓✓ Successfully sent complete audio to frontend ✓✓✓")
        logger.info(f"[TTS] Message sent: type=audio_output, format=wav, audio_length={len(audio_b64)}")
        logger.info(f"[TTS] ⚡ Total TTS generation time: {total_tts_time:.2f} seconds")
        logger.info(f"[TTS] ⚡ TTS speed: {len(full_response) / total_tts_time:.1f} chars/second")
        
    except asyncio.TimeoutError:
        logger.error("TTS generation timed out")
        current_ws = websocket_connections.get(connection_id)
        if current_ws and current_ws.client_state.name == "CONNECTED":
            await current_ws.send_json({
                "type": "error",
                "message": "TTS generation timed out. The response may be too long."
            })
    except ValueError as e:
        # This is our custom error for "No audio generated"
        logger.error(f"TTS generation failed: {e}", exc_info=True)
        try:
            current_ws = websocket_connections.get(connection_id)
            if current_ws and current_ws.client_state.name == "CONNECTED":
                await current_ws.send_json({
                    "type": "error",
                    "message": f"TTS error: {str(e)}"
                })
        except Exception as send_error:
            logger.error(f"Failed to send TTS error message: {send_error}")
    except Exception as e:
        logger.error(f"Error generating/sending TTS: {e}", exc_info=True)
        try:
            current_ws = websocket_connections.get(connection_id)
            if current_ws and current_ws.client_state.name == "CONNECTED":
                await current_ws.send_json({
                    "type": "error",
                    "message": f"TTS error: {str(e)}"
                })
        except Exception as send_error:
            logger.error(f"Failed to send TTS error message: {send_error}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    connection_id = id(websocket)
    
    # Initialize audio buffer for this connection
    audio_buffers[connection_id] = create_audio_buffer()
    websocket_connections[connection_id] = websocket
    await websocket.send_json({
        "type": "connection_ready",
        "connection_id": connection_id
    })
    
    # Keepalive task to prevent timeout during long operations
    keepalive_task = None
    
    async def send_keepalive():
        """Send periodic keepalive messages to prevent timeout"""
        try:
            while True:
                await asyncio.sleep(30)  # Send keepalive every 30 seconds
                current_ws = websocket_connections.get(connection_id)
                if current_ws and current_ws.client_state.name == "CONNECTED":
                    try:
                        await current_ws.send_json({
                            "type": "keepalive",
                            "timestamp": time.time()
                        })
                        logger.debug(f"Sent keepalive to connection {connection_id}")
                    except Exception as e:
                        logger.debug(f"Failed to send keepalive: {e}")
                        break
                else:
                    break
        except asyncio.CancelledError:
            logger.debug("Keepalive task cancelled")
        except Exception as e:
            logger.debug(f"Keepalive task error: {e}")
    
    try:
        # Load ASR model on first connection
        if asr_engine:
            asr_engine.load_model()
        
        # Start keepalive task
        keepalive_task = asyncio.create_task(send_keepalive())
        
        while True:
            # Receive message with timeout to allow keepalive checks
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=60.0)
            except asyncio.TimeoutError:
                # Timeout is OK - just check connection and continue
                if websocket.client_state.name != "CONNECTED":
                    logger.warning("WebSocket disconnected during receive timeout")
                    break
                # Send keepalive and continue
                try:
                    await websocket.send_json({
                        "type": "keepalive",
                        "timestamp": time.time()
                    })
                except Exception:
                    break
                continue
            message_type = data.get("type")
            
            if message_type == "start_call":
                # Initialize call
                audio_buffers[connection_id] = create_audio_buffer()
                await websocket.send_json({
                    "type": "call_started"
                })
                await websocket.send_json({
                    "type": "call_status",
                    "status": "listening"
                })
                logger.info("Call started")
            
            elif message_type == "end_call":
                # Process any remaining audio
                buffer = audio_buffers.get(connection_id)
                if buffer and (buffer['chunks'] or buffer.get('pcm_chunks')):
                    await process_audio_buffer(websocket, connection_id)
                
                # Clean up
                if connection_id in audio_buffers:
                    if audio_buffers[connection_id].get('silence_check_task'):
                        audio_buffers[connection_id]['silence_check_task'].cancel()
                    del audio_buffers[connection_id]
                
                await websocket.send_json({
                    "type": "call_ended"
                })
                logger.info("Call ended")
            
            elif message_type == "audio_stream_chunk":
                audio_b64 = data.get("audio")
                if not audio_b64:
                    continue
                
                buffer = audio_buffers.get(connection_id)
                if not buffer:
                    logger.warning(f"No buffer found for connection {connection_id}")
                    continue
                
                sample_rate = asr_engine.sample_rate if asr_engine else 16000
                analysis = analyze_audio_chunk(audio_b64, sample_rate)
                await process_audio_analysis(connection_id, analysis, websocket)
            
            elif message_type == "audio_chunk":
                audio_b64 = data.get("audio")
                if not audio_b64:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Empty audio payload received."
                    })
                    continue
                
                try:
                    pcm_audio = webm_base64_to_pcm(
                        audio_b64,
                        sample_rate=asr_engine.sample_rate if asr_engine else 16000
                    )
                    logger.info(f"Converted audio: {len(pcm_audio)} bytes PCM")
                    transcript = asr_engine.transcribe_audio(pcm_audio) if asr_engine else ""
                    logger.info(f"Transcription result: '{transcript}' (length: {len(transcript)})")
                except AudioConversionError as e:
                    logger.error(f"Audio conversion failed: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                    continue
                except Exception as e:
                    logger.error(f"ASR processing failed: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": f"ASR error: {str(e)}"
                    })
                    continue
                
                if transcript:
                    await websocket.send_json({
                        "type": "transcription",
                        "text": transcript
                    })
                    await handle_user_text(websocket, transcript)
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "No speech detected in audio chunk."
                    })
                
            elif message_type == "text_input":
                # User sent text directly
                user_text = data.get("text", "")
                if user_text:
                    await handle_user_text(websocket, user_text)
            
            elif message_type == "clear_history":
                # Clear conversation history
                llm_engine.clear_history()
                await websocket.send_json({
                    "type": "history_cleared"
                })
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        # Cancel keepalive task
        if keepalive_task:
            keepalive_task.cancel()
            try:
                await keepalive_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"Error cancelling keepalive task: {e}")
        
        websocket_connections.pop(connection_id, None)
        sessions_to_close = [
            session_id
            for session_id, session in webrtc_sessions.items()
            if session.connection_id == connection_id
        ]
        for session_id in sessions_to_close:
            session = webrtc_sessions.pop(session_id, None)
            if session:
                await session.close()
        # Clean up audio buffer and chunk history
        if connection_id in audio_buffers:
            buffer = audio_buffers[connection_id]
            if buffer.get('silence_check_task'):
                buffer['silence_check_task'].cancel()
            del audio_buffers[connection_id]
        
        # Only close WebSocket if it's still open
        # WebSocketDisconnect means the client already closed it
        if websocket.client_state.name == "CONNECTED":
            try:
                await websocket.close()
            except Exception as e:
                logger.debug(f"Error closing WebSocket (may already be closed): {e}")


if __name__ == "__main__":
    import uvicorn
    # Get port from environment variable or default to 8000
    port = int(os.getenv("PORT", 8000))
    # Increase timeout settings for WebSocket connections to prevent disconnections
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        timeout_keep_alive=75,  # Keep connections alive for 75 seconds
        timeout_graceful_shutdown=10  # Graceful shutdown timeout
    )

