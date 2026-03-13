# Frontend-Backend Connection Guide

## 🔌 Connection Architecture

Your application uses **two types of connections**:

1. **WebSocket** (Primary) - Real-time bidirectional communication
2. **HTTP REST API** (Secondary) - Configuration endpoints

## 📡 WebSocket Connection (Main Communication)

### How It Works

The frontend connects via **WebSocket** at `ws://localhost:8000/ws` for real-time communication:

**Location**: `frontend/src/App.jsx` (line 16)
```javascript
const websocket = new WebSocket('ws://localhost:8000/ws');
```

### What Goes Through WebSocket

1. **Audio Data** - Recorded audio chunks sent as base64-encoded WebM
2. **Transcriptions** - Speech-to-text results from backend
3. **LLM Responses** - Streaming text chunks from the language model
4. **Audio Output** - TTS audio as base64-encoded WAV
5. **Error Messages** - Real-time error notifications

### Message Types

**Frontend → Backend:**
- `audio_chunk` - Audio recording data
- `text_input` - Direct text input
- `clear_history` - Clear conversation history

**Backend → Frontend:**
- `transcription` - Recognized speech text
- `llm_stream_chunk` - Streaming LLM response chunks
- `llm_response` - Complete LLM response
- `audio_output` - Synthesized speech audio
- `error` - Error messages

## 🌐 HTTP REST API (Configuration Only)

### Endpoints Used

**Location**: `frontend/src/services/api.js`

1. **GET `/config`** - Get current agent configuration
2. **POST `/config`** - Update agent configuration
3. **POST `/llm/respond`** - (Not currently used, WebSocket preferred)
4. **POST `/tts/speak`** - (Not currently used, WebSocket preferred)

**Note**: The ConfigPanel component uses HTTP API, but the main conversation uses WebSocket.

## 🔍 How to See WebSocket Connections in Browser DevTools

### Chrome/Edge DevTools

1. **Open DevTools** (F12)
2. **Go to Network tab**
3. **Filter by "WS"** (WebSocket) - Click the filter dropdown and select "WS"
4. **Look for `ws://localhost:8000/ws`**
5. **Click on the WebSocket connection** to see:
   - **Messages tab** - All sent/received messages
   - **Headers** - Connection details
   - **Frames** - Individual WebSocket frames

### Firefox DevTools

1. **Open DevTools** (F12)
2. **Go to Network tab**
3. **Filter by "WS"** (WebSocket)
4. **Click on the connection** to see messages

### What You'll See

**In the Messages tab:**
```
→ {"type":"audio_chunk","audio":"UklGRiQAAABXQVZFZm10..."}
← {"type":"transcription","text":"hello"}
← {"type":"llm_stream_chunk","text":"Hello"}
← {"type":"llm_stream_chunk","text":" there"}
← {"type":"llm_response","text":"Hello there!","user_text":"hello"}
← {"type":"audio_output","audio":"UklGRnoGAABXQVZFZm10...","format":"wav"}
```

## 🐛 Troubleshooting

### Can't See WebSocket in Network Tab

1. **Refresh the page** - WebSocket connects on page load
2. **Check filter** - Make sure "WS" filter is selected
3. **Clear network log** - Clear and reload to see new connections
4. **Check console** - Look for "WebSocket connected" message

### WebSocket Not Connecting

**Check Console for errors:**
- `WebSocket connection to 'ws://localhost:8000/ws' failed`
- Usually means backend is not running on port 8000

**Verify:**
1. Backend is running: `python backend/main.py`
2. Backend is on port 8000 (check terminal output)
3. No firewall blocking the connection

### Connection Status Indicator

The UI shows connection status:
- **Green dot + "Connected"** - WebSocket is active
- **Red dot + "Disconnected"** - WebSocket failed or closed

**Location**: `frontend/src/App.jsx` (lines 105-108)

## 📊 Connection Flow Diagram

```
Frontend (React)
    │
    ├─→ WebSocket (ws://localhost:8000/ws)
    │   ├─→ Send: audio_chunk
    │   ├─→ Receive: transcription
    │   ├─→ Receive: llm_stream_chunk (streaming)
    │   ├─→ Receive: llm_response
    │   └─→ Receive: audio_output
    │
    └─→ HTTP API (http://localhost:8000)
        ├─→ GET /config
        └─→ POST /config
```

## 🔧 Code Locations

### Frontend WebSocket Setup
- **File**: `frontend/src/App.jsx`
- **Lines**: 14-42 (connection setup)
- **Lines**: 60-78 (audio recording and sending)

### Frontend Message Handling
- **File**: `frontend/src/components/ConversationPanel.jsx`
- **Lines**: 24-89 (WebSocket message handlers)

### Backend WebSocket Endpoint
- **File**: `backend/main.py`
- **Lines**: 269-351 (WebSocket handler)

### Backend HTTP Endpoints
- **File**: `backend/main.py`
- **Lines**: 122-206 (REST API routes)

## 💡 Why WebSocket Instead of HTTP?

1. **Real-time** - Bidirectional communication without polling
2. **Streaming** - Can send LLM responses chunk by chunk
3. **Efficiency** - Single persistent connection vs multiple HTTP requests
4. **Low Latency** - No HTTP overhead for each message
5. **Audio Streaming** - Better for sending/receiving audio data

## 🧪 Testing the Connection

### Test WebSocket Connection

1. Open browser console (F12)
2. Look for: `WebSocket connected` message
3. Check Network tab → WS filter → Should see `ws://localhost:8000/ws`
4. Click on it → Messages tab → Should see messages flowing

### Test HTTP API

1. Open browser console
2. Run:
   ```javascript
   fetch('http://localhost:8000/config')
     .then(r => r.json())
     .then(console.log)
   ```
3. Should return configuration JSON

## 📝 Summary

- **Main communication**: WebSocket at `ws://localhost:8000/ws`
- **Configuration**: HTTP REST API at `http://localhost:8000/config`
- **To see WebSocket**: Network tab → Filter by "WS"
- **Connection status**: Shown in UI header (green/red dot)

The reason you don't see regular API calls is because the app uses WebSocket for real-time communication, which appears in a separate section of the Network tab!



