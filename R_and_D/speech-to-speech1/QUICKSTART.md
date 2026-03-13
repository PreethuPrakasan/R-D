# Quick Start Guide

Get up and running in 5 minutes!

## Prerequisites Check

- [ ] Python 3.10+ installed
- [ ] Node.js 18+ installed  
- [ ] Ollama installed and running
- [ ] Microphone available

## Fast Setup

### 1. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Install Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 3. Setup Ollama Model

```bash
# Pull a model (choose one)
ollama pull mistral
# or
ollama pull llama3
```

### 4. Run Application

**Terminal 1 - Backend:**
```bash
cd backend
python main.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```

### 5. Open Browser

Navigate to: http://localhost:3000

## First Test

1. Click "Start Recording"
2. Say: "Hello, how are you?"
3. Click "Stop Recording"
4. Click "Send"
5. Wait for agent response and audio playback

## Troubleshooting

**Backend won't start:**
- Check if port 8000 is free
- Ensure virtual environment is activated
- Verify Ollama is running: `ollama list`

**Frontend won't start:**
- Check if port 3000 is free
- Run `npm install` again

**No audio output:**
- Check browser console for errors
- Verify TTS model downloaded (first run takes time)
- Try typing instead of voice input

**WebSocket disconnected:**
- Ensure backend is running on port 8000
- Check browser console for connection errors

## Next Steps

- Customize agent in `backend/config/agent_config.json`
- Try different Ollama models
- Explore the UI configuration panel

For detailed installation, see [INSTALL.md](INSTALL.md)

