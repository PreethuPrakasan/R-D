# Real-Time Speech-to-Speech Conversational AI

A complete end-to-end, real-time Speech-to-Speech (S2S) conversational application using **only open-source models**. The application is modular and allows easy customization of agent personalities (financial advisor, health assistant, insurance advisor, etc.).

## 🏗️ Architecture

```
Microphone Input → Streaming ASR → LLM (Ollama) → TTS → Speaker Output
```

### Core Components

- **ASR**: Vosk for low-latency, on-device speech recognition
- **LLM**: Local open-source models via Ollama (Mistral, LLaMA 3, Gemma, Phi-3, etc.)
- **TTS**: Coqui TTS (with pyttsx3 fallback) for fast, natural speech synthesis

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Ollama installed and running
- Microphone access

### Installation

1. **Clone and setup Python environment:**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

2. **Install ASR (Vosk):**
```bash
# Vosk will be installed via pip requirements
# Download a Vosk model (e.g., vosk-model-small-en-us-0.15)
# Place it in backend/models/vosk/ or download automatically
```

3. **Install TTS:**
```bash
# Coqui TTS will be installed via pip requirements
# Models will be downloaded automatically on first run
# Falls back to pyttsx3 (system voices) if Coqui TTS unavailable
```

4. **Install Ollama and pull a model:**
```bash
# Install Ollama from https://ollama.ai
# Pull a model:
ollama pull mistral
# or
ollama pull llama3
```

5. **Setup Frontend:**
```bash
cd frontend
npm install
```

6. **Run the application:**
```bash
# Terminal 1: Start backend
cd backend
python main.py

# Terminal 2: Start frontend
cd frontend
npm start
```

7. **Access the application:**
   - Open http://localhost:3000 in your browser
   - Allow microphone access when prompted
   - Click "Start Conversation" to begin

## 📁 Project Structure

```
speech-to-speech/
├── backend/
│   ├── main.py                 # FastAPI server entry point
│   ├── asr/
│   │   └── vosk_asr.py        # Vosk ASR implementation
│   ├── llm/
│   │   └── ollama_llm.py      # Ollama LLM integration
│   ├── tts/
│   │   └── piper_tts.py       # Piper TTS implementation
│   ├── config/
│   │   └── agent_config.json  # Agent personality configuration
│   ├── models/                # Downloaded models directory
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Main React component
│   │   ├── components/        # React components
│   │   └── services/          # API services
│   └── package.json
└── README.md
```

## 🎭 Customizing Agent Personality

Edit `backend/config/agent_config.json`:

```json
{
  "agent_role": "Financial Advisor",
  "agent_description": "You are an expert financial advisor helping users plan investments, budgeting, and long-term wealth growth.",
  "tone": "Friendly, confident, and professional",
  "language": "English",
  "system_prompt_template": "You are a {agent_role}. {agent_description}. Your tone should be {tone}. Always be helpful, concise, and conversational."
}
```

The application will automatically reload the configuration when changed.

## 🔧 Configuration

### Backend Configuration

- **Port**: Default 8000 (change in `backend/main.py`)
- **Ollama Base URL**: Default http://localhost:11434
- **Model Paths**: Configured in respective modules

### Frontend Configuration

- **API URL**: Default http://localhost:8000 (change in `frontend/src/services/api.js`)

## 🎯 Features

- ✅ Real-time streaming ASR
- ✅ Local LLM via Ollama
- ✅ Fast TTS synthesis
- ✅ WebSocket-based low-latency communication
- ✅ Customizable agent personalities
- ✅ Live transcription display
- ✅ Audio playback controls
- ✅ Conversation history

## 🚧 Extensibility (Future Features)

- Knowledge-base retrieval (PDF/Docs) using embeddings
- Personas selectable from UI
- Multi-language ASR & TTS
- Conversation logs saving
- Wake-word activation
- Real-time translation mode

## 📝 License

MIT License

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a pull request.

