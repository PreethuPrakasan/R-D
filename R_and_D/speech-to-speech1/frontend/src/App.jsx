import React, { useState, useEffect, useRef } from 'react';
import ConversationPanel from './components/ConversationPanel';
import ConfigPanel from './components/ConfigPanel';
import './App.css';

function App() {
  const [ws, setWs] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  useEffect(() => {
    // Connect to WebSocket
    const websocket = new WebSocket('ws://localhost:8000/ws');
    
    websocket.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    };
    
    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };
    
    websocket.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      // Attempt to reconnect after 3 seconds
      setTimeout(() => {
        setWs(new WebSocket('ws://localhost:8000/ws'));
      }, 3000);
    };
    
    setWs(websocket);
    
    return () => {
      websocket.close();
    };
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm'
      });
      
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        
        // Convert to base64 and send to backend
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64Audio = reader.result.split(',')[1];
          if (ws && isConnected) {
            ws.send(JSON.stringify({
              type: 'audio_chunk',
              audio: base64Audio
            }));
          }
        };
        reader.readAsDataURL(audioBlob);
        
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorder.start(1000); // Collect data every second
      setIsRecording(true);
    } catch (error) {
      console.error('Error starting recording:', error);
      alert('Could not access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleConfigUpdate = (config) => {
    console.log('Configuration updated:', config);
    // The backend will automatically reload the config
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🎙️ Speech-to-Speech AI</h1>
        <p>Real-time conversational AI with open-source models</p>
        <div className="status-indicator">
          <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}></span>
          <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
        </div>
      </header>

      <div className="main-content">
        <div className="content-grid">
          <div className="left-panel">
            <ConversationPanel
              ws={ws}
              isConnected={isConnected}
              onStart={startRecording}
              onStop={stopRecording}
              isRecording={isRecording}
            />
          </div>

          <div className="right-panel">
            <button
              onClick={() => setShowConfig(!showConfig)}
              className="config-toggle"
            >
              {showConfig ? 'Hide' : 'Show'} Configuration
            </button>
            
            {showConfig && (
              <ConfigPanel onConfigUpdate={handleConfigUpdate} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;

