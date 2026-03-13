# Project Structure

## Directory Layout

```
speech-to-speech/
├── backend/                    # Python FastAPI backend
│   ├── main.py                 # FastAPI server entry point
│   ├── asr/                    # Speech Recognition module
│   │   ├── __init__.py
│   │   └── vosk_asr.py         # Vosk ASR implementation
│   ├── llm/                    # Language Model module
│   │   ├── __init__.py
│   │   └── ollama_llm.py       # Ollama LLM integration
│   ├── tts/                    # Text-to-Speech module
│   │   ├── __init__.py
│   │   └── piper_tts.py        # TTS implementation (Coqui/pyttsx3)
│   ├── config/                 # Configuration files
│   │   └── agent_config.json   # Agent personality config
│   ├── models/                 # AI model storage
│   │   ├── vosk/               # Vosk ASR models
│   │   └── piper/              # TTS models (if needed)
│   ├── scripts/                # Utility scripts
│   │   └── download_models.py  # Model download helper
│   └── requirements.txt        # Python dependencies
│
├── frontend/                   # React frontend
│   ├── public/
│   │   └── index.html          # HTML template
│   ├── src/
│   │   ├── App.jsx             # Main React component
│   │   ├── App.css             # Main styles
│   │   ├── index.js            # React entry point
│   │   ├── index.css           # Global styles
│   │   ├── components/         # React components
│   │   │   ├── ConversationPanel.jsx
│   │   │   ├── ConversationPanel.css
│   │   │   ├── ConfigPanel.jsx
│   │   │   └── ConfigPanel.css
│   │   └── services/           # API services
│   │       └── api.js          # API client
│   └── package.json            # Node.js dependencies
│
├── venv/                       # Python virtual environment (created)
├── .gitignore                  # Git ignore rules
├── README.md                   # Main documentation
├── INSTALL.md                  # Detailed installation guide
├── QUICKSTART.md               # Quick start guide
├── setup.py                    # Setup script
├── start_backend.bat/sh        # Backend startup scripts
└── start_frontend.bat/sh       # Frontend startup scripts
```

## Module Architecture

### Backend Modules

#### 1. ASR (Automatic Speech Recognition)
- **File**: `backend/asr/vosk_asr.py`
- **Class**: `VoskASR`
- **Purpose**: Convert speech audio to text
- **Features**:
  - Streaming audio processing
  - Real-time transcription
  - Low-latency on-device processing

#### 2. LLM (Large Language Model)
- **File**: `backend/llm/ollama_llm.py`
- **Class**: `OllamaLLM`
- **Purpose**: Generate conversational responses
- **Features**:
  - Local model via Ollama
  - Personality customization
  - Conversation history management
  - Streaming support

#### 3. TTS (Text-to-Speech)
- **File**: `backend/tts/piper_tts.py`
- **Class**: `PiperTTS`
- **Purpose**: Convert text to speech audio
- **Features**:
  - Coqui TTS (primary)
  - pyttsx3 fallback
  - Multiple voice options

#### 4. Main Server
- **File**: `backend/main.py`
- **Purpose**: FastAPI server with WebSocket support
- **Endpoints**:
  - `GET /` - Health check
  - `GET /config` - Get agent config
  - `POST /config` - Update agent config
  - `POST /llm/respond` - Get LLM response
  - `POST /tts/speak` - Generate TTS audio
  - `WS /ws` - WebSocket for real-time communication

### Frontend Components

#### 1. App Component
- **File**: `frontend/src/App.jsx`
- **Purpose**: Main application container
- **Features**:
  - WebSocket connection management
  - Microphone recording
  - Layout management

#### 2. Conversation Panel
- **File**: `frontend/src/components/ConversationPanel.jsx`
- **Purpose**: Display and manage conversations
- **Features**:
  - Live transcript display
  - Conversation history
  - Recording controls
  - Audio playback

#### 3. Config Panel
- **File**: `frontend/src/components/ConfigPanel.jsx`
- **Purpose**: Agent personality configuration
- **Features**:
  - Role customization
  - Tone settings
  - Preset personalities
  - Real-time updates

## Data Flow

```
User Speech (Microphone)
    ↓
Frontend: MediaRecorder → WebSocket
    ↓
Backend: WebSocket → ASR (Vosk)
    ↓
Transcribed Text
    ↓
LLM (Ollama) → Response Text
    ↓
TTS (Coqui/pyttsx3) → Audio
    ↓
WebSocket → Frontend
    ↓
Audio Playback
```

## Configuration

### Agent Personality
- **Location**: `backend/config/agent_config.json`
- **Fields**:
  - `agent_role`: Role name (e.g., "Financial Advisor")
  - `agent_description`: Detailed description
  - `tone`: Communication tone
  - `language`: Language setting
  - `system_prompt_template`: Prompt template

### Backend Settings
- **Port**: 8000 (configurable in `main.py`)
- **Ollama URL**: http://localhost:11434
- **CORS**: Enabled for localhost:3000

### Frontend Settings
- **Port**: 3000 (React default)
- **API URL**: http://localhost:8000

## Extension Points

### Adding New ASR Engine
1. Create new class in `backend/asr/`
2. Implement `start_stream()` and `transcribe_audio()` methods
3. Update `backend/main.py` to use new engine

### Adding New LLM Provider
1. Create new class in `backend/llm/`
2. Implement `generate_response()` method
3. Support personality loading
4. Update `backend/main.py` to use new provider

### Adding New TTS Engine
1. Create new class in `backend/tts/`
2. Implement `synthesize()` method
3. Update `backend/main.py` to use new engine

### Adding Frontend Features
1. Create new component in `frontend/src/components/`
2. Add to `App.jsx` if needed
3. Update API service if new endpoints needed

## Dependencies

### Backend
- **FastAPI**: Web framework
- **Vosk**: ASR engine
- **TTS/Coqui**: TTS engine
- **pyttsx3**: TTS fallback
- **Ollama**: Via HTTP API (external service)
- **WebSockets**: Real-time communication

### Frontend
- **React**: UI framework
- **Axios**: HTTP client
- **WebSocket API**: Browser WebSocket

## Model Storage

Models are stored in `backend/models/`:
- **Vosk models**: `backend/models/vosk/`
- **TTS models**: Auto-downloaded by Coqui TTS
- **Ollama models**: Managed by Ollama service

## Logging

Backend logging is configured in `backend/main.py`:
- Level: INFO
- Format: Timestamp, Logger, Level, Message
- Output: Console

## Security Notes

- CORS is enabled for development (localhost only)
- No authentication implemented (add for production)
- WebSocket connections are not secured (use WSS for production)
- Models run locally (no data sent to external services except Ollama)

