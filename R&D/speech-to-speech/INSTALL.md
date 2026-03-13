# Installation Guide

Complete step-by-step installation instructions for the Speech-to-Speech application.

## Prerequisites

- **Python 3.10+** - [Download Python](https://www.python.org/downloads/)
- **Node.js 18+** - [Download Node.js](https://nodejs.org/)
- **Ollama** - [Download Ollama](https://ollama.ai/)
- **Microphone** - For voice input

## Step 1: Clone/Setup Project

```bash
# Navigate to project directory
cd speech-to-speech
```

## Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

## Step 3: Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Note:** Some packages may require additional system dependencies:
- **pyaudio**: On Linux, you may need: `sudo apt-get install portaudio19-dev python3-pyaudio`
- **vosk**: Should install automatically via pip

## Step 4: Install ASR Model (Vosk)

Vosk models will be downloaded automatically on first use, or you can download manually:

```bash
# Option 1: Use the download script
python backend/scripts/download_models.py

# Option 2: Manual download
# Visit https://alphacephei.com/vosk/models
# Download "vosk-model-small-en-us-0.15" (or larger for better accuracy)
# Extract to backend/models/vosk/
```

## Step 5: Install TTS

### Option A: Coqui TTS (Recommended - Better Quality)

Coqui TTS will download models automatically on first use. The default model is lightweight and fast.

```bash
# Already included in requirements.txt
# Models download automatically on first run
```

### Option B: pyttsx3 (Fallback - System Voices)

If Coqui TTS fails, pyttsx3 will be used automatically (uses system voices).

**Windows:** Uses SAPI5 voices (built-in)  
**Linux:** Requires `espeak`: `sudo apt-get install espeak`  
**Mac:** Uses built-in voices

## Step 6: Install Ollama and Pull Model

1. **Install Ollama:**
   - Visit https://ollama.ai/
   - Download and install for your OS
   - Verify: `ollama --version`

2. **Pull a Model:**
   ```bash
   # Recommended models (choose one):
   ollama pull mistral        # Fast, good quality
   ollama pull llama3         # Larger, better quality
   ollama pull gemma:2b       # Very fast, smaller
   ollama pull phi3           # Fast, efficient
   ```

3. **Verify Model:**
   ```bash
   ollama list
   ```

4. **Start Ollama (if not running):**
   - Ollama usually runs as a service automatically
   - Verify: `curl http://localhost:11434/api/tags`

## Step 7: Install Frontend Dependencies

```bash
cd frontend
npm install
```

## Step 8: Configure Agent Personality (Optional)

Edit `backend/config/agent_config.json` to customize the agent:

```json
{
  "agent_role": "Financial Advisor",
  "agent_description": "You are an expert financial advisor...",
  "tone": "Friendly, confident, and professional",
  "language": "English"
}
```

## Step 9: Run the Application

### Terminal 1: Start Backend

```bash
# Activate virtual environment first
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

cd backend
python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Terminal 2: Start Frontend

```bash
cd frontend
npm start
```

The browser should open automatically to http://localhost:3000

## Step 10: Test the Application

1. **Allow Microphone Access:** When prompted, allow microphone access
2. **Check Connection:** Status indicator should show "Connected" (green dot)
3. **Start Conversation:**
   - Click "Start Recording" and speak
   - Or type a message and click "Send"
4. **Verify Flow:**
   - Your speech/text → ASR → LLM → TTS → Audio output

## Troubleshooting

### Backend Issues

**Port 8000 already in use:**
```bash
# Change port in backend/main.py
uvicorn.run(app, host="0.0.0.0", port=8001)
```

**Vosk model not found:**
```bash
# Download model manually
python backend/scripts/download_models.py
```

**Ollama connection error:**
- Ensure Ollama is running: `ollama list`
- Check if model is pulled: `ollama list`
- Verify API: `curl http://localhost:11434/api/tags`

**TTS not working:**
- Coqui TTS: Models download on first use (may take time)
- pyttsx3: Install system dependencies (espeak on Linux)

### Frontend Issues

**Port 3000 already in use:**
- React will prompt to use another port
- Or set: `PORT=3001 npm start`

**WebSocket connection failed:**
- Ensure backend is running on port 8000
- Check CORS settings in `backend/main.py`

**Microphone not working:**
- Check browser permissions
- Try different browser (Chrome recommended)
- Verify microphone in system settings

### General Issues

**Python import errors:**
- Ensure virtual environment is activated
- Reinstall: `pip install -r backend/requirements.txt`

**Node module errors:**
- Delete `node_modules` and `package-lock.json`
- Reinstall: `npm install`

## Quick Start Script

For convenience, you can use the setup script:

```bash
# Windows
python setup.py

# Linux/Mac
python3 setup.py
```

This will:
- Create virtual environment
- Install Python dependencies
- Install Node dependencies
- Create necessary directories

## Next Steps

- Customize agent personality in `backend/config/agent_config.json`
- Try different Ollama models for different capabilities
- Explore the codebase to add features
- Check README.md for extensibility options

## Support

If you encounter issues:
1. Check the logs in the terminal
2. Verify all prerequisites are installed
3. Ensure all services are running
4. Check the troubleshooting section above

