import React, { useState, useEffect, useRef, useCallback } from 'react';
import ConversationPanel from './components/ConversationPanel';
import ConfigPanel from './components/ConfigPanel';
import './App.css';

function App() {
  const [ws, setWs] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isInCall, setIsInCall] = useState(false);
  const [callStatus, setCallStatus] = useState('idle'); // idle, listening, speaking, processing
  const [showConfig, setShowConfig] = useState(false);
  const [connectionId, setConnectionId] = useState(null);
  const [isMicrophoneMuted, setIsMicrophoneMuted] = useState(false);
  const peerConnectionRef = useRef(null);
  const audioStreamRef = useRef(null);
  const webrtcSessionIdRef = useRef(null);
  const isInCallRef = useRef(false); // Ref to track call state for callbacks

  // Use a ref to store the message handler callback from ConversationPanel
  const conversationPanelHandlerRef = useRef(null);
  
  // Function to toggle microphone mute
  const toggleMicrophoneMute = () => {
    if (!audioStreamRef.current) {
      console.warn('[App.jsx] No audio stream available to mute');
      return;
    }
    
    const newMutedState = !isMicrophoneMuted;
    setIsMicrophoneMuted(newMutedState);
    
    // Enable/disable all audio tracks
    audioStreamRef.current.getTracks().forEach(track => {
      track.enabled = !newMutedState;
      console.log(`[App.jsx] Audio track ${track.kind} ${newMutedState ? 'muted' : 'unmuted'}`);
    });
    
    console.log(`[App.jsx] Microphone ${newMutedState ? 'muted' : 'unmuted'}`);
  };
  
  // Reconnection state
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectDelayRef = useRef(3000); // Start with 3 seconds

  const connectWebSocket = useCallback(() => {
    // Get API URL from environment variable or default to localhost:8000
    const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    const wsUrl = apiUrl.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws';
    
    console.log('[App.jsx] Connecting to WebSocket:', wsUrl);
    const websocket = new WebSocket(wsUrl);
    
    websocket.onopen = () => {
      console.log('[App.jsx] WebSocket connected, readyState:', websocket.readyState);
      setIsConnected(true);
      reconnectAttemptsRef.current = 0; // Reset on successful connection
      reconnectDelayRef.current = 3000; // Reset delay
    };
    
    websocket.onerror = (error) => {
      console.error('[App.jsx] WebSocket error:', error);
      setIsConnected(false);
    };
    
    websocket.onclose = (event) => {
      console.log('[App.jsx] WebSocket disconnected', {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean
      });
      setIsConnected(false);
      
      // Clear any existing reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      
      // Don't reconnect if it was a clean close or max attempts reached
      if (event.wasClean || reconnectAttemptsRef.current >= maxReconnectAttempts) {
        if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          console.error('[App.jsx] Max reconnection attempts reached. Please refresh the page.');
        }
        return;
      }
      
      // Attempt to reconnect with exponential backoff
      reconnectAttemptsRef.current += 1;
      const delay = Math.min(reconnectDelayRef.current * reconnectAttemptsRef.current, 30000); // Max 30 seconds
      
      console.log(`[App.jsx] Attempting to reconnect in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);
      
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log('[App.jsx] Reconnecting...');
        connectWebSocket();
      }, delay);
    };
    
    // Set up a SINGLE onmessage handler that routes to ConversationPanel
    // This ensures ConversationPanel gets ALL messages
    websocket.onmessage = (event) => {
      console.log('[App.jsx] WebSocket message received, routing to ConversationPanel...');
      
      // First, handle connection_ready for connection_id
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'connection_ready') {
          console.log('[App.jsx] Received connection_ready, connection_id:', data.connection_id);
          setConnectionId(data.connection_id);
        }
        // Log for debugging
        console.log('[App.jsx] Message type:', data.type, '- will be handled by ConversationPanel');
      } catch (e) {
        console.error('[App.jsx] Failed to parse message:', e);
      }
      
      // Route to ConversationPanel handler if it's set up
      // ConversationPanel will set this ref when its handler is ready
      if (conversationPanelHandlerRef.current) {
        console.log('[App.jsx] Routing message to ConversationPanel handler');
        conversationPanelHandlerRef.current(event);
      } else {
        console.warn('[App.jsx] ⚠ ConversationPanel handler not ready yet - message may be lost!');
        console.warn('[App.jsx] Message type was:', JSON.parse(event.data)?.type);
      }
    };
    
    // Set ws state immediately
    setWs(websocket);
    
    console.log('[App.jsx] WebSocket created, onmessage handler set up');
    console.log('[App.jsx] Waiting for ConversationPanel to register its handler...');
    
    return () => {
      websocket.close();
      conversationPanelHandlerRef.current = null;
    };
  }, []);

  const startCall = async () => {
    if (!connectionId) {
      console.error('No connection_id available. Waiting for WebSocket connection...');
      alert('Please wait for connection to be established.');
      return;
    }

    try {
      // Get user media
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });
      audioStreamRef.current = stream;
      
      // Create RTCPeerConnection
      const pc = new RTCPeerConnection({
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' }
        ]
      });
      peerConnectionRef.current = pc;
      
      // Add audio track to peer connection
      stream.getTracks().forEach(track => {
        pc.addTrack(track, stream);
        console.log('Added audio track to peer connection');
      });
      
      // Handle ICE candidates
      pc.onicecandidate = async (event) => {
        if (event.candidate && webrtcSessionIdRef.current) {
          try {
            const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
            const response = await fetch(`${apiUrl}/webrtc/candidate`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                session_id: webrtcSessionIdRef.current,
                candidate: event.candidate.candidate,
                sdpMid: event.candidate.sdpMid,
                sdpMLineIndex: event.candidate.sdpMLineIndex,
              }),
            });
            if (!response.ok) {
              console.error('Failed to send ICE candidate');
            }
          } catch (error) {
            console.error('Error sending ICE candidate:', error);
          }
        }
      };
      
      // Handle connection state changes
      pc.onconnectionstatechange = () => {
        console.log('WebRTC connection state:', pc.connectionState);
        // Don't auto-end call on WebRTC failure - WebSocket is still open for responses
        // Only log the state change, let user manually end call if needed
        if (pc.connectionState === 'failed') {
          console.warn('WebRTC connection failed, but keeping call active for responses');
        } else if (pc.connectionState === 'disconnected') {
          console.warn('WebRTC disconnected, but keeping call active for responses');
        }
      };
      
      // Create offer
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      
      console.log('Created WebRTC offer, sending to backend...');
      
      // Send offer to backend
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/webrtc/offer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sdp: offer.sdp,
          type: offer.type,
          connection_id: connectionId,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to create WebRTC session: ${response.statusText}`);
      }
      
      const answerData = await response.json();
      webrtcSessionIdRef.current = answerData.session_id;
      
      console.log('Received WebRTC answer, setting remote description...');
      
      // Set remote description (answer)
      await pc.setRemoteDescription(new RTCSessionDescription({
        type: answerData.type,
        sdp: answerData.sdp,
      }));
      
      console.log('WebRTC session established');
      
      isInCallRef.current = true;
      setIsInCall(true);
      setCallStatus('listening');
      
      // Notify backend that call started (for WebSocket control messages)
      if (ws && isConnected) {
        ws.send(JSON.stringify({
          type: 'start_call'
        }));
      }
    } catch (error) {
      console.error('Error starting WebRTC call:', error);
      alert(`Could not start call: ${error.message}`);
      // Clean up on error
      if (audioStreamRef.current) {
        audioStreamRef.current.getTracks().forEach(track => track.stop());
        audioStreamRef.current = null;
      }
      if (peerConnectionRef.current) {
        peerConnectionRef.current.close();
        peerConnectionRef.current = null;
      }
    }
  };

  const endCall = async () => {
    console.log('Ending call...');
    isInCallRef.current = false;
    
    // Close WebRTC session
    if (webrtcSessionIdRef.current) {
      try {
        const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
        await fetch(`${apiUrl}/webrtc/close`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: webrtcSessionIdRef.current,
          }),
        });
        webrtcSessionIdRef.current = null;
      } catch (error) {
        console.error('Error closing WebRTC session:', error);
      }
    }
    
    // Close peer connection
    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
      peerConnectionRef.current = null;
      console.log('Peer connection closed');
    }
    
    // Stop audio tracks
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach(track => track.stop());
      audioStreamRef.current = null;
      console.log('Audio stream tracks stopped');
    }
    
    setIsInCall(false);
    setCallStatus('idle');
    
    // Notify backend that call ended
    if (ws && isConnected) {
      ws.send(JSON.stringify({
        type: 'end_call'
      }));
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
            {ws && (
              <ConversationPanel
                ws={ws}
                isConnected={isConnected}
                connectionId={connectionId}
                onStartCall={startCall}
                onEndCall={endCall}
                isInCall={isInCall}
                callStatus={callStatus}
                onCallStatusChange={setCallStatus}
                messageHandlerRef={conversationPanelHandlerRef}
                isMicrophoneMuted={isMicrophoneMuted}
                onToggleMicrophoneMute={toggleMicrophoneMute}
              />
            )}
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

