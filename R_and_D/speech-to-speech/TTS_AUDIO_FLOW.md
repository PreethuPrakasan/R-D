# TTS Audio Flow: Backend to Frontend

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ BACKEND: TTS Generation                                         │
├─────────────────────────────────────────────────────────────────┤
│ 1. TTS Engine generates audio (bytes)                           │
│    Location: backend/tts/piper_tts.py::synthesize()            │
│    Output: WAV file bytes (e.g., 173748 bytes)                  │
│                                                                  │
│ 2. Audio is validated                                           │
│    - Checks for RIFF header (valid WAV)                         │
│    - Logs audio size                                            │
│                                                                  │
│ 3. Audio bytes are base64 encoded                               │
│    Location: backend/main.py::handle_user_text()                 │
│    Code: audio_b64 = base64.b64encode(audio_data).decode()     │
│    Result: Base64 string (e.g., 231664 chars)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ WebSocket JSON Message
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ BACKEND: WebSocket Send                                         │
├─────────────────────────────────────────────────────────────────┤
│ await current_ws.send_json({                                    │
│     "type": "audio_output",                                     │
│     "audio": audio_b64,        // Base64 encoded string        │
│     "format": "wav"                                             │
│ })                                                               │
│                                                                  │
│ Location: backend/main.py:1230-1234                             │
│ Logs: "[TTS] ✓ Encoded audio: X bytes -> Y base64 chars"      │
│       "✓ Successfully sent audio_output to frontend"           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ WebSocket Message
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ FRONTEND: WebSocket Receive                                      │
├─────────────────────────────────────────────────────────────────┤
│ 1. Message received in ConversationPanel.jsx                    │
│    Handler: case 'audio_output'                                 │
│    Location: frontend/src/components/ConversationPanel.jsx:187  │
│                                                                  │
│ 2. Base64 decoded to Blob                                       │
│    Code: const audioBlob = base64ToBlob(data.audio, 'audio/wav')│
│    Function: base64ToBlob() at line 315                         │
│    Process:                                                      │
│      - Removes data URL prefix if present                       │
│      - Decodes base64 to binary                                 │
│      - Creates Uint8Array                                      │
│      - Creates Blob with MIME type 'audio/wav'                 │
│                                                                  │
│ 3. Blob URL created                                             │
│    Code: const audioUrl = URL.createObjectURL(audioBlob)        │
│    Result: blob:http://localhost:3000/...                      │
│                                                                  │
│ 4. Audio element updated                                        │
│    Code: audioRef.current.src = audioUrl                       │
│         audioRef.current.load()                                 │
│                                                                  │
│ 5. Audio playback triggered                                     │
│    Code: audioRef.current.play()                                │
│    Auto-play with error handling                                │
└─────────────────────────────────────────────────────────────────┘
```

## Code Locations

### Backend (Python)

1. **TTS Generation**: `backend/tts/piper_tts.py::synthesize()`
   - Generates WAV audio bytes
   - Returns: `bytes` (raw audio data)

2. **Audio Encoding & Sending**: `backend/main.py::handle_user_text()` (lines 1224-1236)
   ```python
   # Encode audio to base64
   audio_b64 = base64.b64encode(audio_data).decode('utf-8')
   
   # Send via WebSocket
   await current_ws.send_json({
       "type": "audio_output",
       "audio": audio_b64,  # Base64 string
       "format": "wav"
   })
   ```

### Frontend (React/JavaScript)

1. **Message Handler**: `frontend/src/components/ConversationPanel.jsx` (lines 187-240)
   ```javascript
   case 'audio_output':
     // Decode base64 to blob
     const audioBlob = base64ToBlob(data.audio, 'audio/wav');
     
     // Create blob URL
     const audioUrl = URL.createObjectURL(audioBlob);
     
     // Set audio source and play
     audioRef.current.src = audioUrl;
     audioRef.current.load();
     audioRef.current.play();
   ```

2. **Base64 Decoder**: `frontend/src/components/ConversationPanel.jsx::base64ToBlob()` (lines 315-334)
   ```javascript
   const base64ToBlob = (base64, mimeType) => {
     // Remove data URL prefix if present
     let base64Data = base64.includes(',') ? base64.split(',')[1] : base64;
     
     // Decode base64
     const byteCharacters = atob(base64Data);
     const byteNumbers = new Array(byteCharacters.length);
     for (let i = 0; i < byteCharacters.length; i++) {
       byteNumbers[i] = byteCharacters.charCodeAt(i);
     }
     const byteArray = new Uint8Array(byteNumbers);
     
     // Create blob
     return new Blob([byteArray], { type: mimeType });
   };
   ```

## Message Format

### WebSocket Message Structure
```json
{
  "type": "audio_output",
  "audio": "UklGRqymAgBXQVZFZm10IBIAAAABAAEAIlYAAESsAAACABAAAABkYXRhhqYC...",
  "format": "wav"
}
```

- **type**: `"audio_output"` - identifies the message type
- **audio**: Base64-encoded WAV file string
- **format**: `"wav"` - audio format identifier

## Data Sizes (Example)

- **Original Audio**: 173,748 bytes (WAV file)
- **Base64 Encoded**: 231,664 characters
- **Compression**: Base64 is ~33% larger than binary

## Logging Points

### Backend Logs
- `[TTS] Audio data read: X bytes`
- `[TTS] ✓ Valid WAV file detected (RIFF header)`
- `[TTS] ✓ Encoded audio: X bytes -> Y base64 chars`
- `[TTS] Base64 preview (first 50 chars): ...`
- `✓ Successfully sent audio_output to frontend`

### Frontend Logs
- `=== RECEIVED AUDIO OUTPUT ===`
- `Audio data length: X`
- `Converting base64 to blob...`
- `Blob created, size: X`
- `Created audio URL: blob:...`
- `✓ Audio playback started successfully`

## Potential Issues & Solutions

### Issue 1: Audio not playing
- **Check**: Browser console for audio play errors
- **Check**: Audio element ref is initialized
- **Check**: Browser autoplay policies (may require user interaction)

### Issue 2: Base64 decoding fails
- **Check**: Base64 string is complete (not truncated)
- **Check**: No data URL prefix issues
- **Check**: MIME type is correct ('audio/wav')

### Issue 3: WebSocket message not received
- **Check**: WebSocket connection state (should be CONNECTED)
- **Check**: Message handler is registered
- **Check**: Backend logs show "Successfully sent audio_output"

## Testing

1. **Test TTS Generation**: `GET /tts/test`
2. **Test Audio Playback**: `GET /tts/test/play`
3. **Test Full Flow**: Use the conversation interface and check logs


