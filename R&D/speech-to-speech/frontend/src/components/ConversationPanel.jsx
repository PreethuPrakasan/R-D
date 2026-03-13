import React, { useState, useRef, useEffect } from 'react';
import './ConversationPanel.css';

const ConversationPanel = ({ ws, isConnected, onStart, onStop, isRecording }) => {
  const [transcript, setTranscript] = useState('');
  const [agentResponse, setAgentResponse] = useState('');
  const [conversationHistory, setConversationHistory] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const audioRef = useRef(null);
  const transcriptEndRef = useRef(null);

  useEffect(() => {
    if (!ws) return;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'transcription':
          setTranscript(data.text);
          break;
        
        case 'llm_response':
          setAgentResponse(data.text);
          setIsProcessing(false);
          // Add to conversation history
          setConversationHistory(prev => [
            ...prev,
            { type: 'user', text: transcript },
            { type: 'assistant', text: data.text }
          ]);
          setTranscript('');
          break;
        
        case 'audio_output':
          // Play audio
          if (audioRef.current) {
            const audioBlob = base64ToBlob(data.audio, 'audio/wav');
            const audioUrl = URL.createObjectURL(audioBlob);
            audioRef.current.src = audioUrl;
            audioRef.current.play().catch(e => console.error('Audio play error:', e));
          }
          break;
        
        case 'error':
          console.error('Error:', data.message);
          setIsProcessing(false);
          break;
        
        default:
          break;
      }
    };
  }, [ws, transcript]);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversationHistory]);

  const base64ToBlob = (base64, mimeType) => {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
  };

  const handleSendText = () => {
    if (!transcript.trim() || !ws || !isConnected) return;
    
    setIsProcessing(true);
    ws.send(JSON.stringify({
      type: 'text_input',
      text: transcript
    }));
  };

  const handleClearHistory = () => {
    setConversationHistory([]);
    setTranscript('');
    setAgentResponse('');
    if (ws && isConnected) {
      ws.send(JSON.stringify({ type: 'clear_history' }));
    }
  };

  return (
    <div className="conversation-panel">
      <div className="conversation-header">
        <h2>Conversation</h2>
        <button 
          onClick={handleClearHistory}
          className="clear-btn"
          disabled={conversationHistory.length === 0}
        >
          Clear History
        </button>
      </div>

      <div className="conversation-history">
        {conversationHistory.length === 0 ? (
          <div className="empty-state">
            <p>Start a conversation by speaking or typing a message.</p>
          </div>
        ) : (
          conversationHistory.map((msg, idx) => (
            <div key={idx} className={`message ${msg.type}`}>
              <div className="message-label">
                {msg.type === 'user' ? 'You' : 'Assistant'}
              </div>
              <div className="message-text">{msg.text}</div>
            </div>
          ))
        )}
        <div ref={transcriptEndRef} />
      </div>

      <div className="input-section">
        <div className="transcript-display">
          <label>Your Input:</label>
          <div className="transcript-text">
            {transcript || (isRecording ? 'Listening...' : 'Type or speak your message')}
          </div>
        </div>

        <div className="controls">
          <button
            onClick={isRecording ? onStop : onStart}
            className={`record-btn ${isRecording ? 'recording' : ''}`}
            disabled={!isConnected}
          >
            {isRecording ? '⏹ Stop Recording' : '🎤 Start Recording'}
          </button>
          
          <button
            onClick={handleSendText}
            className="send-btn"
            disabled={!transcript.trim() || !isConnected || isProcessing}
          >
            {isProcessing ? 'Processing...' : 'Send'}
          </button>
        </div>

        {agentResponse && (
          <div className="agent-response">
            <label>Agent Response:</label>
            <div className="response-text">{agentResponse}</div>
          </div>
        )}

        <audio ref={audioRef} controls style={{ width: '100%', marginTop: '10px' }} />
      </div>
    </div>
  );
};

export default ConversationPanel;

