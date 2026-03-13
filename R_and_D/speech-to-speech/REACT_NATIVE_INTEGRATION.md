# React Native Android Integration Guide

This guide explains how to integrate the Speech-to-Speech backend with a React Native Android application.

## 📋 Table of Contents

1. [Backend Changes Required](#backend-changes-required)
2. [React Native Setup](#react-native-setup)
3. [WebSocket Connection](#websocket-connection)
4. [Audio Handling](#audio-handling)
5. [Network Configuration](#network-configuration)
6. [Testing](#testing)

---

## 🔧 Backend Changes Required

### 1. Update CORS Configuration

**File**: `backend/main.py` (lines 42-48)

**Current** (only allows localhost):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Updated** (allows all origins for mobile apps):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for mobile apps
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**OR** (more secure - allow specific origins):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # Add your React Native app's origin if needed
        # For React Native, you might not need specific origins
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. Update Server Host Configuration

**File**: `backend/main.py` (line 1807)

**Current**:
```python
uvicorn.run(app, host="0.0.0.0", port=8000)
```

**This is already correct!** `0.0.0.0` allows connections from any network interface, which is needed for mobile devices.

### 3. Optional: Add Environment Variable for API URL

Create a `.env` file or use environment variables to configure the API URL:

```python
# In backend/main.py, add at the top:
import os
API_BASE_URL = os.getenv("API_BASE_URL", "http://0.0.0.0:8000")
```

---

## 📱 React Native Setup

### 1. Install Required Dependencies

```bash
npm install react-native-websocket
# OR use the built-in WebSocket (available in React Native)
```

For audio handling:
```bash
npm install react-native-sound
# OR
npm install expo-av  # If using Expo
```

For microphone access:
```bash
npm install react-native-audio-recorder-player
# OR
npm install expo-av  # If using Expo (includes audio recording)
```

### 2. Android Permissions

**File**: `android/app/src/main/AndroidManifest.xml`

Add these permissions:
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
```

### 3. Network Security Configuration (Android 9+)

**File**: `android/app/src/main/res/xml/network_security_config.xml` (create if doesn't exist)

```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">YOUR_SERVER_IP</domain>
        <domain includeSubdomains="true">localhost</domain>
        <domain includeSubdomains="true">10.0.2.2</domain> <!-- Android Emulator -->
    </domain-config>
</network-security-config>
```

**File**: `android/app/src/main/AndroidManifest.xml`

Add to `<application>` tag:
```xml
<application
    android:networkSecurityConfig="@xml/network_security_config"
    ...>
```

---

## 🔌 WebSocket Connection

### React Native WebSocket Implementation

**File**: `src/services/websocketService.js`

```javascript
class WebSocketService {
  constructor() {
    this.ws = null;
    this.reconnectInterval = 3000;
    this.maxReconnectAttempts = 5;
    this.reconnectAttempts = 0;
    this.shouldReconnect = true;
    this.messageHandlers = [];
    this.reconnectTimeout = null;
    this.connectionState = 'disconnected'; // 'connecting', 'connected', 'disconnected'
    this.serverUrl = null;
  }

  connect(serverUrl) {
    // Replace localhost with your server IP
    // For Android Emulator: use 10.0.2.2 instead of localhost
    // For Physical Device: use your computer's IP (e.g., 192.168.1.100)
    this.serverUrl = serverUrl || 'ws://YOUR_SERVER_IP:8000/ws';
    
    // Don't reconnect if already connecting or connected
    if (this.connectionState === 'connecting' || this.connectionState === 'connected') {
      console.log('WebSocket already connecting/connected');
      return;
    }
    
    this.connectionState = 'connecting';
    console.log(`[WebSocket] Connecting to: ${this.serverUrl}`);
    
    try {
      this.ws = new WebSocket(this.serverUrl);
    } catch (error) {
      console.error('[WebSocket] Failed to create WebSocket:', error);
      this.connectionState = 'disconnected';
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      console.log('[WebSocket] Connected');
      this.connectionState = 'connected';
      this.reconnectAttempts = 0; // Reset on successful connection
      this.onOpen();
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Ignore keepalive messages (they're just for connection health)
        if (data.type === 'keepalive') {
          console.log('[WebSocket] Received keepalive');
          return;
        }
        
        this.handleMessage(data);
      } catch (error) {
        console.error('[WebSocket] Failed to parse message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error);
      this.connectionState = 'disconnected';
      this.onError(error);
    };

    this.ws.onclose = (event) => {
      console.log('[WebSocket] Disconnected', {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean
      });
      this.connectionState = 'disconnected';
      this.onClose();
      
      // Don't reconnect if it was a clean close or max attempts reached
      if (!this.shouldReconnect || event.wasClean || this.reconnectAttempts >= this.maxReconnectAttempts) {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          console.error('[WebSocket] Max reconnection attempts reached');
        }
        return;
      }
      
      this.scheduleReconnect();
    };
  }

  scheduleReconnect() {
    // Clear any existing reconnect timeout
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }
    
    // Exponential backoff: 3s, 6s, 12s, 24s, 30s (max)
    this.reconnectAttempts += 1;
    const delay = Math.min(this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1), 30000);
    
    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    this.reconnectTimeout = setTimeout(() => {
      this.connect(this.serverUrl);
    }, delay);
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(message));
      } catch (error) {
        console.error('[WebSocket] Failed to send message:', error);
        // Connection might be broken, trigger reconnect
        if (this.shouldReconnect) {
          this.scheduleReconnect();
        }
      }
    } else {
      console.warn('[WebSocket] Cannot send - not connected. State:', this.ws?.readyState);
      // Try to reconnect if not already connecting
      if (this.shouldReconnect && this.connectionState === 'disconnected') {
        this.scheduleReconnect();
      }
    }
  }

  handleMessage(data) {
    // Route messages to registered handlers
    this.messageHandlers.forEach(handler => {
      try {
        handler(data);
      } catch (error) {
        console.error('[WebSocket] Error in message handler:', error);
      }
    });
  }

  onMessage(handler) {
    this.messageHandlers.push(handler);
  }

  removeMessageHandler(handler) {
    this.messageHandlers = this.messageHandlers.filter(h => h !== handler);
  }

  disconnect() {
    console.log('[WebSocket] Disconnecting...');
    this.shouldReconnect = false;
    
    // Clear reconnect timeout
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    this.connectionState = 'disconnected';
  }

  isConnected() {
    return this.connectionState === 'connected' && 
           this.ws && 
           this.ws.readyState === WebSocket.OPEN;
  }

  getConnectionState() {
    return this.connectionState;
  }
}

export default new WebSocketService();
```

### Usage in React Native Component

```javascript
import React, { useEffect, useState } from 'react';
import { View, Text } from 'react-native';
import WebSocketService from './services/websocketService';

function ConversationScreen() {
  const [isConnected, setIsConnected] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [agentResponse, setAgentResponse] = useState('');

  useEffect(() => {
    // Get server URL from config or environment
    const serverUrl = 'ws://YOUR_SERVER_IP:8000/ws';
    
    // Connect to WebSocket
    WebSocketService.connect(serverUrl);

    // Register message handler
    WebSocketService.onMessage((data) => {
      switch (data.type) {
        case 'connection_ready':
          setIsConnected(true);
          break;
        case 'transcription':
          setTranscript(data.text);
          break;
        case 'llm_response':
          setAgentResponse(data.text);
          break;
        case 'audio_output':
          // Handle audio playback (see Audio Handling section)
          handleAudioOutput(data.audio, data.format);
          break;
        case 'error':
          console.error('Backend error:', data.message);
          break;
      }
    });

    return () => {
      WebSocketService.disconnect();
    };
  }, []);

  const sendText = (text) => {
    WebSocketService.send({
      type: 'text_input',
      text: text
    });
  };

  return (
    <View>
      <Text>Status: {isConnected ? 'Connected' : 'Disconnected'}</Text>
      <Text>Transcript: {transcript}</Text>
      <Text>Response: {agentResponse}</Text>
    </View>
  );
}
```

---

## 🎤 Audio Handling

### Recording Audio (React Native)

**Using `react-native-audio-recorder-player`:**

```javascript
import AudioRecorderPlayer from 'react-native-audio-recorder-player';

const audioRecorderPlayer = new AudioRecorderPlayer();

// Start recording
const startRecording = async () => {
  try {
    const result = await audioRecorderPlayer.startRecorder();
    console.log('Recording started:', result);
  } catch (error) {
    console.error('Failed to start recording:', error);
  }
};

// Stop recording and send to backend
const stopRecording = async () => {
  try {
    const result = await audioRecorderPlayer.stopRecorder();
    console.log('Recording stopped:', result);
    
    // Read audio file and convert to base64
    const audioBase64 = await readAudioFileAsBase64(result);
    
    // Send to backend via WebSocket
    WebSocketService.send({
      type: 'audio_chunk',
      audio: audioBase64,
      format: 'wav' // or 'mp3' depending on what you're recording
    });
  } catch (error) {
    console.error('Failed to stop recording:', error);
  }
};

// Helper function to read audio file as base64
const readAudioFileAsBase64 = async (filePath) => {
  const RNFS = require('react-native-fs');
  return await RNFS.readFile(filePath, 'base64');
};
```

**Using `expo-av` (if using Expo):**

```javascript
import { Audio } from 'expo-av';

const [recording, setRecording] = useState(null);

const startRecording = async () => {
  try {
    await Audio.requestPermissionsAsync();
    await Audio.setAudioModeAsync({
      allowsRecordingIOS: true,
      playsInSilentModeIOS: true,
    });

    const { recording } = await Audio.Recording.createAsync(
      Audio.RecordingOptionsPresets.HIGH_QUALITY
    );
    setRecording(recording);
  } catch (err) {
    console.error('Failed to start recording', err);
  }
};

const stopRecording = async () => {
  if (!recording) return;
  
  await recording.stopAndUnloadAsync();
  const uri = recording.getURI();
  
  // Convert to base64 and send
  const audioBase64 = await convertUriToBase64(uri);
  WebSocketService.send({
    type: 'audio_chunk',
    audio: audioBase64,
    format: 'wav'
  });
  
  setRecording(null);
};
```

### Playing Audio (React Native)

**Using `react-native-sound`:**

```javascript
import Sound from 'react-native-sound';

const playAudio = (base64Audio, format = 'wav') => {
  // Convert base64 to file or use directly
  const audioData = `data:audio/${format};base64,${base64Audio}`;
  
  // Save to temporary file
  const filePath = saveBase64ToFile(base64Audio, format);
  
  // Play audio
  const sound = new Sound(filePath, '', (error) => {
    if (error) {
      console.error('Failed to load sound:', error);
      return;
    }
    
    sound.play((success) => {
      if (success) {
        console.log('Audio played successfully');
      } else {
        console.log('Audio playback failed');
      }
      sound.release();
    });
  });
};
```

**Using `expo-av` (if using Expo):**

```javascript
import { Audio } from 'expo-av';

const playAudio = async (base64Audio, format = 'wav') => {
  try {
    const { sound } = await Audio.Sound.createAsync(
      { uri: `data:audio/${format};base64,${base64Audio}` },
      { shouldPlay: true }
    );
    
    await sound.playAsync();
  } catch (error) {
    console.error('Failed to play audio:', error);
  }
};
```

---

## 🌐 Network Configuration

### Finding Your Server IP Address

**Windows:**
```powershell
ipconfig
# Look for IPv4 Address (e.g., 192.168.1.100)
```

**Mac/Linux:**
```bash
ifconfig
# OR
ip addr show
```

### Android Emulator Configuration

- **Android Emulator** uses `10.0.2.2` to access the host machine's `localhost`
- Use: `ws://10.0.2.2:8000/ws`

### Physical Device Configuration

- Use your computer's **local IP address** (e.g., `192.168.1.100`)
- Use: `ws://192.168.1.100:8000/ws`
- **Important**: Both devices must be on the same network (WiFi)

### Production/Cloud Deployment

- Use your server's domain or IP: `ws://your-server.com:8000/ws`
- Or use WSS (WebSocket Secure): `wss://your-server.com:8000/ws`
- Update backend to support WSS if needed

---

## 🧪 Testing

### 1. Test Backend Accessibility

From your React Native app or a test tool:

```javascript
// Test WebSocket connection
const testConnection = () => {
  const ws = new WebSocket('ws://YOUR_SERVER_IP:8000/ws');
  ws.onopen = () => console.log('Connected!');
  ws.onerror = (error) => console.error('Connection failed:', error);
};
```

### 2. Test Audio Recording

1. Start recording
2. Speak into microphone
3. Stop recording
4. Check if audio is sent to backend (check backend logs)

### 3. Test Audio Playback

1. Send a text message
2. Wait for `audio_output` message
3. Verify audio plays correctly

---

## 📝 Summary of Changes

### Backend (Minimal Changes)
- ✅ Update CORS to allow all origins (or specific ones)
- ✅ Server already runs on `0.0.0.0` (good for mobile)

### React Native App
- ✅ Install WebSocket library (built-in or `react-native-websocket`)
- ✅ Install audio libraries (`react-native-sound` or `expo-av`)
- ✅ Install audio recording library (`react-native-audio-recorder-player` or `expo-av`)
- ✅ Add Android permissions
- ✅ Configure network security for Android 9+
- ✅ Replace `localhost` with actual server IP
- ✅ Implement WebSocket connection service
- ✅ Implement audio recording
- ✅ Implement audio playback

### Network
- ✅ Use `10.0.2.2` for Android Emulator
- ✅ Use your computer's IP for physical devices
- ✅ Ensure both devices on same network

---

## 🚀 Quick Start Checklist

- [ ] Update backend CORS configuration
- [ ] Find your server IP address
- [ ] Install React Native dependencies
- [ ] Add Android permissions
- [ ] Configure network security
- [ ] Implement WebSocket service
- [ ] Implement audio recording
- [ ] Implement audio playback
- [ ] Test connection from React Native app
- [ ] Test audio recording and playback

---

## 💡 Additional Notes

1. **WebRTC**: The current implementation uses WebRTC for some features. React Native has `react-native-webrtc` if you need WebRTC functionality.

2. **Base64 Encoding**: React Native handles base64 encoding/decoding similarly to web browsers.

3. **Error Handling**: Add proper error handling for network issues, audio permissions, etc.

4. **State Management**: Consider using Redux or Context API for managing WebSocket state across your app.

5. **Background Tasks**: For background audio recording/playback, you may need additional configuration.

---

## 🆘 Troubleshooting

### Connection Issues
- **Problem**: Can't connect to WebSocket
- **Solution**: 
  - Verify server IP is correct
  - Check firewall settings
  - Ensure both devices on same network
  - For emulator, use `10.0.2.2` instead of `localhost`

### Audio Issues
- **Problem**: Can't record audio
- **Solution**: 
  - Check Android permissions
  - Verify microphone permissions granted
  - Check audio format compatibility

### CORS Issues
- **Problem**: CORS errors in logs
- **Solution**: 
  - Update backend CORS configuration
  - Ensure `allow_origins` includes your app's origin

---

Good luck with your integration! 🎉

