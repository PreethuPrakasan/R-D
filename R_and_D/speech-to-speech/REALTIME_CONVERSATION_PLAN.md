# Real-Time Live Conversation Implementation Plan

## 🎯 Goal
Convert from "record and send" to real-time live conversation with:
- "Start Call" button for continuous conversation
- Continuous audio streaming to backend
- Automatic processing on 2+ seconds of silence
- Real-time transcription display
- Seamless conversation flow

## 📊 Current vs Target Architecture

### Current (Chunk-Based)
```
User clicks "Start Recording" → Records chunks → 
User clicks "Stop Recording" → Sends complete audio → 
Backend processes → Returns response
```

### Target (Real-Time Streaming)
```
User clicks "Start Call" → Continuous audio stream → 
Backend processes in real-time → 
Auto-detect silence (2s) → Process → 
Stream response back → Continue listening
```

## 🏗️ Implementation Plan

### Phase 1: Frontend - Continuous Audio Streaming

#### 1.1 Update UI Components
**File**: `frontend/src/App.jsx`

**Changes:**
- Replace "Start Recording" / "Stop Recording" with "Start Call" / "End Call"
- Add "Call Status" indicator (Connected, Listening, Processing, Speaking)
- Show real-time transcription as user speaks
- Display "Listening..." when waiting for speech

**New State:**
```javascript
const [isInCall, setIsInCall] = useState(false);
const [callStatus, setCallStatus] = useState('idle'); // idle, listening, processing, speaking
const [liveTranscript, setLiveTranscript] = useState('');
```

#### 1.2 Implement Continuous Audio Streaming
**File**: `frontend/src/App.jsx`

**Changes:**
- Stream audio chunks continuously (every 100-200ms) instead of waiting for stop
- Send audio chunks via WebSocket as they're recorded
- Don't wait for user to stop - backend handles silence detection

**Implementation:**
```javascript
// Stream audio chunks continuously
mediaRecorder.ondataavailable = (event) => {
  if (event.data.size > 0 && isInCall) {
    // Convert to base64 and send immediately
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64Audio = reader.result.split(',')[1];
      ws.send(JSON.stringify({
        type: 'audio_stream_chunk',
        audio: base64Audio,
        timestamp: Date.now()
      }));
    };
    reader.readAsDataURL(event.data);
  }
};

// Start with smaller intervals for real-time feel
mediaRecorder.start(100); // Every 100ms instead of 1000ms
```

#### 1.3 Add Silence Detection Indicator
- Show visual indicator when silence is detected
- Countdown or progress bar for silence duration
- Auto-trigger message when 2 seconds reached

### Phase 2: Backend - Streaming Audio Processing

#### 2.1 Add Voice Activity Detection (VAD)
**File**: `backend/utils/vad.py` (NEW)

**Purpose:**
- Detect when user is speaking vs silent
- Trigger processing after 2 seconds of silence
- Buffer audio chunks until silence detected

**Implementation Options:**
1. **Use faster-whisper VAD** (already has VAD built-in)
2. **Use webrtcvad** (lightweight, fast)
3. **Use silero-vad** (accurate, modern)

**Recommended**: Use faster-whisper's built-in VAD (already available)

#### 2.2 Update WebSocket Handler
**File**: `backend/main.py`

**New Message Types:**
- `audio_stream_chunk` - Continuous audio chunks
- `silence_detected` - Backend detects silence
- `processing_started` - Backend starts processing
- `live_transcription` - Real-time transcription as user speaks
- `call_ended` - User ends call

**Changes:**
```python
# Buffer for accumulating audio chunks
audio_buffer = []
last_audio_time = None
silence_threshold = 2.0  # 2 seconds

if message_type == "audio_stream_chunk":
    # Add to buffer
    audio_buffer.append(audio_data)
    last_audio_time = time.time()
    
    # Check for silence
    if time.time() - last_audio_time > silence_threshold:
        # Process accumulated audio
        await process_audio_buffer(audio_buffer)
        audio_buffer.clear()
```

#### 2.3 Implement Streaming ASR
**File**: `backend/asr/whisper_asr.py`

**Changes:**
- Add method to process streaming audio chunks
- Use faster-whisper's streaming capabilities
- Return partial transcriptions in real-time

**New Method:**
```python
def transcribe_streaming(self, audio_chunks):
    """Process streaming audio chunks with real-time transcription"""
    # Accumulate chunks
    # Process when silence detected
    # Return partial + final results
```

### Phase 3: Real-Time Transcription Display

#### 3.1 Frontend - Live Transcription
**File**: `frontend/src/components/ConversationPanel.jsx`

**Changes:**
- Add "live transcript" area that updates in real-time
- Show partial transcriptions as user speaks
- Update final transcription when silence detected
- Clear and start new when processing begins

**New Message Handler:**
```javascript
case 'live_transcription':
  setLiveTranscript(data.text); // Update in real-time
  break;

case 'silence_detected':
  // Finalize current transcription
  setTranscript(liveTranscript);
  setLiveTranscript(''); // Clear for next
  setIsProcessing(true);
  break;
```

#### 3.2 Backend - Stream Partial Results
**File**: `backend/main.py`

**Implementation:**
- Send partial transcriptions as they're generated
- Use faster-whisper's streaming mode
- Send updates every 200-500ms

### Phase 4: Automatic Processing Flow

#### 4.1 Silence Detection Logic
**File**: `backend/main.py`

**Flow:**
1. Receive audio chunks continuously
2. Use VAD to detect speech vs silence
3. Track silence duration
4. When silence > 2 seconds:
   - Process accumulated audio
   - Send transcription
   - Generate LLM response
   - Synthesize TTS
   - Send response
   - Clear buffer and continue listening

#### 4.2 State Management
**Backend States:**
- `listening` - Receiving audio, waiting for speech
- `speaking` - User is speaking, accumulating audio
- `silence_detected` - 2+ seconds of silence, processing
- `processing` - ASR + LLM + TTS in progress
- `responding` - Sending TTS audio back

### Phase 5: Enhanced User Experience

#### 5.1 Visual Feedback
- **Listening indicator** - Pulsing animation when waiting
- **Speaking indicator** - Visual feedback when user speaks
- **Processing indicator** - Show when backend is processing
- **Silence countdown** - Show progress toward 2-second threshold

#### 5.2 Audio Feedback
- Optional: Play subtle sound when silence detected
- Optional: Play sound when processing starts

#### 5.3 Conversation Flow
- Show conversation history in real-time
- Display user speech as it's transcribed
- Show assistant response as it streams
- Auto-scroll to latest message

## 🔧 Technical Implementation Details

### Frontend Changes

#### File: `frontend/src/App.jsx`
```javascript
// New state
const [isInCall, setIsInCall] = useState(false);
const [callStatus, setCallStatus] = useState('idle');
const [silenceDuration, setSilenceDuration] = useState(0);

// Start call
const startCall = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mediaRecorder = new MediaRecorder(stream, {
    mimeType: 'audio/webm'
  });
  
  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0 && isInCall) {
      // Send chunk immediately
      sendAudioChunk(event.data);
    }
  };
  
  // Stream every 100ms for real-time feel
  mediaRecorder.start(100);
  setIsInCall(true);
  setCallStatus('listening');
};

// Send audio chunk
const sendAudioChunk = (audioBlob) => {
  const reader = new FileReader();
  reader.onloadend = () => {
    const base64Audio = reader.result.split(',')[1];
    ws.send(JSON.stringify({
      type: 'audio_stream_chunk',
      audio: base64Audio
    }));
  };
  reader.readAsDataURL(audioBlob);
};
```

#### File: `frontend/src/components/ConversationPanel.jsx`
```javascript
// New message handlers
case 'live_transcription':
  setLiveTranscript(data.text);
  break;

case 'silence_detected':
  setTranscript(liveTranscript);
  setLiveTranscript('');
  setIsProcessing(true);
  break;

case 'call_status':
  setCallStatus(data.status);
  break;
```

### Backend Changes

#### File: `backend/main.py`
```python
# Add audio buffer management
audio_buffers = {}  # Per-connection buffers

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connection_id = id(websocket)
    audio_buffers[connection_id] = {
        'chunks': [],
        'last_audio_time': None,
        'is_speaking': False
    }
    
    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "audio_stream_chunk":
                buffer = audio_buffers[connection_id]
                buffer['chunks'].append(data.get("audio"))
                buffer['last_audio_time'] = time.time()
                buffer['is_speaking'] = True
                
                # Check for silence
                await check_silence_and_process(websocket, connection_id)
                
            elif message_type == "start_call":
                await websocket.send_json({"type": "call_started"})
                
            elif message_type == "end_call":
                # Process any remaining audio
                await process_remaining_audio(websocket, connection_id)
                await websocket.send_json({"type": "call_ended"})
                break
                
    finally:
        if connection_id in audio_buffers:
            del audio_buffers[connection_id]

async def check_silence_and_process(websocket, connection_id):
    """Check if silence threshold reached and process"""
    buffer = audio_buffers[connection_id]
    
    # Use asyncio to check periodically
    while buffer['is_speaking']:
        await asyncio.sleep(0.5)  # Check every 500ms
        if buffer['last_audio_time']:
            silence_duration = time.time() - buffer['last_audio_time']
            if silence_duration >= 2.0:  # 2 seconds
                # Process accumulated audio
                await process_audio_buffer(websocket, connection_id)
                buffer['is_speaking'] = False
                break

async def process_audio_buffer(websocket, connection_id):
    """Process accumulated audio chunks"""
    buffer = audio_buffers[connection_id]
    if not buffer['chunks']:
        return
    
    # Combine all chunks
    combined_audio = combine_audio_chunks(buffer['chunks'])
    
    # Convert and transcribe
    pcm_audio = webm_base64_to_pcm(combined_audio)
    transcript = asr_engine.transcribe_audio(pcm_audio)
    
    if transcript:
        await websocket.send_json({
            "type": "transcription",
            "text": transcript
        })
        await handle_user_text(websocket, transcript)
    
    # Clear buffer
    buffer['chunks'] = []
    buffer['last_audio_time'] = None
```

## 📋 Implementation Checklist

### Phase 1: Frontend Streaming (Priority: High)
- [ ] Replace "Start Recording" with "Start Call" button
- [ ] Implement continuous audio streaming (100ms intervals)
- [ ] Add call status indicator
- [ ] Update UI to show "In Call" state
- [ ] Add "End Call" button

### Phase 2: Backend Streaming Handler (Priority: High)
- [ ] Add audio buffer management per connection
- [ ] Implement silence detection logic
- [ ] Add `audio_stream_chunk` message handler
- [ ] Add `start_call` and `end_call` handlers
- [ ] Test silence detection (2-second threshold)

### Phase 3: Real-Time Transcription (Priority: Medium)
- [ ] Implement live transcription display
- [ ] Add `live_transcription` message type
- [ ] Update UI to show real-time text
- [ ] Handle partial vs final transcriptions

### Phase 4: VAD Integration (Priority: Medium)
- [ ] Integrate VAD for better silence detection
- [ ] Use faster-whisper's VAD or webrtcvad
- [ ] Fine-tune silence threshold
- [ ] Test with various audio conditions

### Phase 5: UX Enhancements (Priority: Low)
- [ ] Add visual indicators (listening, speaking, processing)
- [ ] Add silence countdown/progress
- [ ] Improve conversation flow
- [ ] Add audio feedback (optional)

## 🎨 UI/UX Design

### Call Interface
```
┌─────────────────────────────────────┐
│  🎙️ Speech-to-Speech AI             │
│  Status: ● In Call                   │
├─────────────────────────────────────┤
│  Conversation History:               │
│  ┌─────────────────────────────────┐ │
│  │ YOU: Hello, how are you?        │ │
│  │ ASSISTANT: I'm doing well...    │ │
│  └─────────────────────────────────┘ │
├─────────────────────────────────────┤
│  Live Transcription:                  │
│  ┌─────────────────────────────────┐ │
│  │ "I need help with..."           │ │
│  │ [Listening... ████░░]          │ │
│  └─────────────────────────────────┘ │
├─────────────────────────────────────┤
│  [🔴 End Call]  [Status: Listening]  │
└─────────────────────────────────────┘
```

### Status Indicators
- **Listening** (Green pulse) - Waiting for speech
- **Speaking** (Blue pulse) - User is speaking
- **Processing** (Yellow pulse) - Backend processing
- **Responding** (Purple pulse) - Playing response

## 🔍 Testing Plan

### Test Cases
1. **Basic Flow**
   - Start call → Speak → Silence → Get response
   
2. **Multiple Turns**
   - Start call → Speak → Get response → Speak again → Get response
   
3. **Silence Detection**
   - Speak → Pause 1.5s → Continue → Pause 2.5s → Should process
   
4. **Long Speech**
   - Speak for 30 seconds → Pause → Should process all
   
5. **Quick Responses**
   - Speak short phrase → Quick silence → Fast response
   
6. **Background Noise**
   - Test with background noise → Should still detect silence correctly

## ⚠️ Potential Challenges

1. **Audio Buffer Management**
   - Need to efficiently combine chunks
   - Handle memory for long conversations
   
2. **Silence Detection Accuracy**
   - May trigger on background noise
   - Need to tune VAD sensitivity
   
3. **Latency**
   - Streaming adds some overhead
   - Need to balance chunk size vs latency
   
4. **Connection Stability**
   - WebSocket may disconnect
   - Need reconnection logic
   
5. **Resource Usage**
   - Continuous processing uses more CPU
   - May need optimization

## 🚀 Quick Start Implementation

### Step 1: Update Frontend (2-3 hours)
1. Change button to "Start Call"
2. Implement continuous streaming
3. Add call status UI

### Step 2: Update Backend (3-4 hours)
1. Add audio buffer management
2. Implement silence detection
3. Update WebSocket handlers

### Step 3: Testing (1-2 hours)
1. Test basic flow
2. Tune silence threshold
3. Fix any issues

**Total Estimated Time: 6-9 hours**

## 📚 Resources

- [WebRTC Audio Streaming](https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder)
- [faster-whisper VAD](https://github.com/guillaumekln/faster-whisper)
- [WebRTC VAD](https://github.com/wiseman/py-webrtcvad)
- [Silero VAD](https://github.com/snakers4/silero-vad)

## ✅ Next Steps

1. Review and approve this plan
2. Start with Phase 1 (Frontend streaming)
3. Then Phase 2 (Backend handling)
4. Iterate and refine based on testing

Would you like me to start implementing any specific phase?



