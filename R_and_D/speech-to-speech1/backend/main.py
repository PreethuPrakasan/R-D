"""
Main FastAPI Server for Speech-to-Speech Application
"""
import base64
import json
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from asr.vosk_asr import VoskASR
from llm.ollama_llm import OllamaLLM
from tts.piper_tts import PiperTTS
from utils.audio_utils import AudioConversionError, webm_base64_to_pcm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Speech-to-Speech API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
asr_engine: Optional[VoskASR] = None
llm_engine: Optional[OllamaLLM] = None
tts_engine: Optional[PiperTTS] = None

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


def initialize_engines():
    """Initialize ASR, LLM, and TTS engines"""
    global asr_engine, llm_engine, tts_engine
    
    try:
        # Initialize ASR
        logger.info("Initializing ASR engine...")
        asr_engine = VoskASR()
        # Don't load model until needed (it's heavy)
        logger.info("ASR engine ready")
        
        # Initialize LLM
        logger.info("Initializing LLM engine...")
        config = load_config()
        llm_engine = OllamaLLM(model="mistral")  # Default model
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
        audio_data = tts_engine.synthesize(request.text)
        
        # Save to temporary file
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_file.write(audio_data)
        temp_file.close()
        
        return FileResponse(
            temp_file.name,
            media_type="audio/wav",
            filename="speech.wav"
        )
    except Exception as e:
        logger.error(f"Error in TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_user_text(websocket: WebSocket, user_text: str):
    """Generate LLM + TTS response for provided user text."""
    if not user_text.strip():
        return
    
    if not llm_engine:
        raise HTTPException(status_code=500, detail="LLM engine not initialized")
    if not tts_engine:
        raise HTTPException(status_code=500, detail="TTS engine not initialized")
    
    # Send LLM response
    try:
        response = llm_engine.generate_response(user_text)
        await websocket.send_json({
            "type": "llm_response",
            "text": response
        })
    except Exception as e:
        logger.error(f"Error generating LLM response: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"LLM error: {str(e)}"
        })
        return
    
    # Send synthesized audio
    try:
        audio_data = tts_engine.synthesize(response)
        audio_b64 = base64.b64encode(audio_data).decode('utf-8')
        
        await websocket.send_json({
            "type": "audio_output",
            "audio": audio_b64,
            "format": "wav"
        })
    except Exception as e:
        logger.error(f"Error generating TTS: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"TTS error: {str(e)}"
        })


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        # Load ASR model on first connection
        if asr_engine and not asr_engine.model:
            asr_engine.load_model()
        
        while True:
            # Receive message
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "audio_chunk":
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
                    transcript = asr_engine.transcribe_audio(pcm_audio) if asr_engine else ""
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
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

