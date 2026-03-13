import React, { useState, useRef, useEffect } from 'react';
import { flushSync } from 'react-dom';
import './ConversationPanel.css';

const ConversationPanel = ({ 
  ws, 
  isConnected, 
  onStartCall, 
  onEndCall, 
  isInCall, 
  callStatus,
  onCallStatusChange,
  messageHandlerRef,
  isMicrophoneMuted,
  onToggleMicrophoneMute
}) => {
  const [transcript, setTranscript] = useState('');
  const [liveTranscript, setLiveTranscript] = useState('');
  const [agentResponse, setAgentResponse] = useState('');
  const [conversationHistory, setConversationHistory] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [pendingUserMessage, setPendingUserMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [silenceDuration, setSilenceDuration] = useState(0);
  const [audioReceived, setAudioReceived] = useState(false);
  const [renderKey, setRenderKey] = useState(0);
  const [isMuted, setIsMuted] = useState(false);
  const [autoMuteAfterTalk, setAutoMuteAfterTalk] = useState(false);
  const isMutedRef = useRef(false);
  const audioRef = useRef(null);
  const transcriptEndRef = useRef(null);
  // Use refs to access current state values in message handler
  const transcriptRef = useRef('');
  const pendingUserMessageRef = useRef('');
  const conversationHistoryRef = useRef([]);
  // Audio queue for sentence-level streaming
  const audioQueueRef = useRef([]);
  const isPlayingAudioRef = useRef(false);
  const currentAudioUrlRef = useRef(null);
  const audioPlaybackQueueRef = useRef([]);  // Queue for streaming audio chunks
  const isProcessingAudioQueueRef = useRef(false);

  // Audio queue management functions (defined early so they're available in message handler)
  const clearAudioQueue = () => {
    audioPlaybackQueueRef.current.forEach(item => {
      URL.revokeObjectURL(item.url);
    });
    audioPlaybackQueueRef.current = [];
    isProcessingAudioQueueRef.current = false;
  };
  
  const playAudioQueue = () => {
    if (isProcessingAudioQueueRef.current || audioPlaybackQueueRef.current.length === 0) {
      return;
    }
    
    if (isMutedRef.current) {
      console.log('[ConversationPanel] Audio muted, clearing queue');
      clearAudioQueue();
      return;
    }
    
    isProcessingAudioQueueRef.current = true;
    const nextItem = audioPlaybackQueueRef.current.shift();
    
    console.log('[ConversationPanel] Playing queued audio, sentence:', nextItem.sentenceNum);
    
    if (!audioRef.current) {
      console.error('[ConversationPanel] audioRef.current is null!');
      isProcessingAudioQueueRef.current = false;
      return;
    }
    
    audioRef.current.src = nextItem.url;
    audioRef.current.load();
    
    const playNext = () => {
      const playPromise = audioRef.current.play();
      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            console.log('[ConversationPanel] ✓ Playing sentence', nextItem.sentenceNum);
          })
          .catch(e => {
            console.error('[ConversationPanel] ✗ Error playing queued audio:', e);
            isProcessingAudioQueueRef.current = false;
            // Try next item
            if (audioPlaybackQueueRef.current.length > 0) {
              playAudioQueue();
            }
          });
      }
    };
    
    // When this audio ends, play next in queue
    const handleEnded = () => {
      console.log('[ConversationPanel] Sentence', nextItem.sentenceNum, 'ended');
      URL.revokeObjectURL(nextItem.url);
      
      // Play next item if available
      if (audioPlaybackQueueRef.current.length > 0) {
        playAudioQueue();
      } else {
        console.log('[ConversationPanel] ✓✓✓ All queued audio completed ✓✓✓');
        isProcessingAudioQueueRef.current = false;
        setAudioReceived(false);
      }
    };
    
    audioRef.current.addEventListener('ended', handleEnded, { once: true });
    audioRef.current.addEventListener('canplay', playNext, { once: true });
    
    // Fallback
    setTimeout(() => {
      if (audioRef.current && audioRef.current.paused) {
        playNext();
      }
    }, 500);
  };

  // Update call status display
  useEffect(() => {
    if (callStatus === 'processing') {
      setIsProcessing(true);
    } else if (callStatus === 'listening' || callStatus === 'speaking') {
      setIsProcessing(false);
    }
  }, [callStatus]);

  useEffect(() => {
    if (!ws) {
      console.warn('[ConversationPanel] WebSocket not available - handler NOT set up');
      return;
    }

    console.log('[ConversationPanel] ===== SETTING UP MESSAGE HANDLER =====');
    console.log('[ConversationPanel] WebSocket details:', {
      readyState: ws.readyState,
      url: ws.url,
      protocol: ws.protocol,
      wsObject: ws
    });
    
    // Test: Send a message to backend to verify connection
    if (ws.readyState === WebSocket.OPEN) {
      console.log('[ConversationPanel] ✓ WebSocket is OPEN, connection ready');
    } else {
      console.warn('[ConversationPanel] ⚠ WebSocket is not OPEN, readyState:', ws.readyState);
    }

    const messageHandler = (event) => {
      console.log('[ConversationPanel] ===== MESSAGE HANDLER CALLED =====');
      console.log('[ConversationPanel] Timestamp:', new Date().toISOString());
      console.log('[ConversationPanel] Raw event data length:', event.data?.length);
      console.log('[ConversationPanel] Raw event data preview:', event.data?.substring(0, 100));
      
      let data;
      try {
        data = JSON.parse(event.data);
        console.log('[ConversationPanel] ✓ Message parsed successfully');
      } catch (e) {
        console.error('[ConversationPanel] ✗ Failed to parse WebSocket message:', e, event.data);
        return;
      }
      
      // Log ALL messages for debugging
      console.log('[ConversationPanel] ✓✓✓ RECEIVED MESSAGE IN HANDLER ✓✓✓');
      console.log('[ConversationPanel] Message type:', data.type);
      console.log('[ConversationPanel] Full message data keys:', Object.keys(data));
      
      // Special handling for important messages
      if (data.type === 'llm_response' || data.type === 'audio_output' || data.type === 'transcription') {
        console.log('[ConversationPanel] ⭐⭐ CRITICAL MESSAGE RECEIVED ⭐⭐');
        console.log('[ConversationPanel] Full message:', JSON.stringify(data).substring(0, 200));
      }
      
      if (data.type === 'llm_response' || data.type === 'audio_output') {
        console.log('[ConversationPanel] ⭐ IMPORTANT MESSAGE ⭐');
        if (data.type === 'audio_output') {
          console.log('[ConversationPanel] Audio message details:', {
            type: data.type,
            format: data.format,
            audioLength: data.audio?.length || 0,
            audioFirstChars: data.audio?.substring(0, 100) || 'NO DATA'
          });
        } else {
          console.log('[ConversationPanel] Full data:', JSON.stringify(data).substring(0, 500));
        }
      }
      
      switch (data.type) {
        case 'connection_ready':
          // Handled in App.jsx, ignore here
          break;

        case 'call_started':
          onCallStatusChange?.('listening');
          break;

        case 'call_ended':
          onCallStatusChange?.('idle');
          setLiveTranscript('');
          setTranscript('');
          break;

        case 'call_status':
          onCallStatusChange?.(data.status);
          if (data.silence_duration !== undefined) {
            setSilenceDuration(data.silence_duration);
          }
          break;

        case 'live_transcription':
          // Real-time transcription as user speaks
          setLiveTranscript(data.text);
          break;

        case 'transcription':
          // Final transcription after silence detected
          console.log('[ConversationPanel] Received transcription:', data.text);
          // Use flushSync to ensure immediate UI update
          flushSync(() => {
            setTranscript(data.text);
            setPendingUserMessage(data.text);
            setLiveTranscript(''); // Clear live transcript
            setAgentResponse('');
            setErrorMessage('');
            setIsProcessing(true);
          });
          onCallStatusChange?.('processing');
          break;

        case 'llm_stream_chunk':
          console.log('Received LLM stream chunk:', data.text);
          setAgentResponse(prev => {
            const newResponse = prev + data.text;
            console.log('Updated agentResponse (streaming):', newResponse.substring(0, 100));
            return newResponse;
          });
          break;
        
        case 'llm_response':
          console.log('=== RECEIVED LLM RESPONSE ===');
          console.log('[ConversationPanel] Response text:', data.text);
          console.log('[ConversationPanel] User text:', data.user_text);
          
          // Clear any existing audio when new response arrives
          // But don't clear src immediately - wait for new audio to arrive
          if (currentAudioUrlRef.current) {
            URL.revokeObjectURL(currentAudioUrlRef.current);
            currentAudioUrlRef.current = null;
          }
          if (audioRef.current) {
            audioRef.current.pause();
            // Don't clear src here - let audio_output handler set it
            // audioRef.current.src = '';  // Removed to prevent empty src error
          }
          
          // Clear audio queue for new response
          clearAudioQueue();
          
          // Get user message from data or from refs (avoid stale closures)
          const userMessage = data.user_text || pendingUserMessageRef.current || transcriptRef.current;
          console.log('[ConversationPanel] User message for history:', userMessage);
          
          // Use flushSync to ensure immediate UI update
          flushSync(() => {
            // Update agent response FIRST (this is what shows in the UI)
            if (data.text) {
              console.log('[ConversationPanel] Setting agentResponse to:', data.text);
              setAgentResponse(data.text);
            }
            
            // Update conversation history - use refs to avoid stale closures
            setConversationHistory(prev => {
              const nextHistory = [...prev];
              // Only add user message if we have one and it's not a duplicate
              if (userMessage && userMessage.trim()) {
                const lastMsg = nextHistory[nextHistory.length - 1];
                if (!lastMsg || lastMsg.type !== 'user' || lastMsg.text !== userMessage.trim()) {
                  nextHistory.push({ type: 'user', text: userMessage.trim() });
                  console.log('[ConversationPanel] Added user message to history');
                }
              }
              // Add assistant response
              if (data.text && data.text.trim()) {
                nextHistory.push({ type: 'assistant', text: data.text.trim() });
                console.log('[ConversationPanel] Added assistant message to history');
              }
              console.log('[ConversationPanel] Updated conversation history, new length:', nextHistory.length);
              return nextHistory;
            });
            
            // Clear pending message
            setPendingUserMessage('');
            setIsProcessing(false);
          });
          
          onCallStatusChange?.('listening'); // Back to listening after response
          // Keep transcript visible for a moment so user can see what they said
          setTimeout(() => setTranscript(''), 2000);
          setSilenceDuration(0);
          break;
        
        case 'ping':
          console.log('Received ping from backend');
          break;
        
        case 'test_message':
          console.log('Received test message from backend:', data.message);
          break;
        
        case 'llm_response_sent':
          console.log('✓ Backend confirmed llm_response was sent:', data.message, 'text_length:', data.text_length);
          break;
        
        case 'audio_output':
          console.log('=== [ConversationPanel] RECEIVED AUDIO OUTPUT ===');
          console.log('[ConversationPanel] Audio data length:', data.audio?.length || 'MISSING');
          console.log('[ConversationPanel] Audio format:', data.format || 'MISSING');
          console.log('[ConversationPanel] Is streaming:', data.is_streaming || false);
          console.log('[ConversationPanel] Sentence num:', data.sentence_num || 'N/A');
          
          if (!data.audio) {
            console.error('[ConversationPanel] ✗ ERROR: No audio data in message!');
            console.error('[ConversationPanel] Message keys:', Object.keys(data));
            break;
          }
          
          // Mark that audio was received
          setAudioReceived(true);
          
          // Handle streaming vs non-streaming audio
          if (data.is_streaming) {
            console.log('[ConversationPanel] Streaming audio chunk received, sentence:', data.sentence_num);
            // For streaming: queue and play sequentially
            // Add to queue
            const mimeType = data.format === 'wav' ? 'audio/wav' : 'audio/mpeg';
            const audioBlob = base64ToBlob(data.audio, mimeType);
            const audioUrl = URL.createObjectURL(audioBlob);
            
            audioPlaybackQueueRef.current.push({
              url: audioUrl,
              sentenceNum: data.sentence_num,
              blob: audioBlob
            });
            
            console.log('[ConversationPanel] Added to queue, queue length:', audioPlaybackQueueRef.current.length);
            
            // Start playing queue if not already playing
            if (!isProcessingAudioQueueRef.current) {
              playAudioQueue();
            }
            break; // Don't process as regular audio
          }
          
          // Non-streaming: clear queue and play this single audio file
          console.log('[ConversationPanel] Non-streaming audio, clearing queue and playing');
          clearAudioQueue();
          isPlayingAudioRef.current = false;
          
          // Convert base64 to blob and play immediately
          try {
            const mimeType = data.format === 'wav' ? 'audio/wav' : 'audio/mpeg';
            console.log('[ConversationPanel] Converting base64 to blob, MIME type:', mimeType);
            
            const audioBlob = base64ToBlob(data.audio, mimeType);
            console.log('[ConversationPanel] ✓ Blob created:', audioBlob.size, 'bytes, type:', audioBlob.type);
            
            // Clean up previous audio URL
            if (currentAudioUrlRef.current) {
              URL.revokeObjectURL(currentAudioUrlRef.current);
              currentAudioUrlRef.current = null;
            }
            
            const audioUrl = URL.createObjectURL(audioBlob);
            currentAudioUrlRef.current = audioUrl;
            console.log('[ConversationPanel] ✓ Created blob URL:', audioUrl);
            
            // Use a small delay to ensure audioRef is ready
            setTimeout(() => {
              if (!audioRef.current) {
                console.error('[ConversationPanel] ✗✗✗ ERROR: audioRef.current is null!');
                return;
              }
              
              console.log('[ConversationPanel] Setting audio src to:', audioUrl);
              audioRef.current.src = audioUrl;
              audioRef.current.load();
              
              console.log('[ConversationPanel] ✓ Audio element loaded, src:', audioRef.current.src);
              console.log('[ConversationPanel] Audio readyState:', audioRef.current.readyState);
              
              // Add event listeners for complete playback tracking
              const handleAudioEnded = () => {
                console.log('[ConversationPanel] ✓✓✓ Audio playback completed successfully ✓✓✓');
                setAudioReceived(false);
                
                // Auto-mute after playback if enabled
                if (autoMuteAfterTalk) {
                  console.log('[ConversationPanel] Audio ended, auto-muting');
                  setIsMuted(true);
                  isMutedRef.current = true;
                }
              };
              
              const handleAudioError = (e) => {
                console.error('[ConversationPanel] ✗ Audio playback error:', e);
                console.error('[ConversationPanel] Audio error details:', audioRef.current?.error);
                setAudioReceived(false);
              };
              
              const handleAudioStalled = () => {
                console.warn('[ConversationPanel] Audio stalled, attempting to resume...');
                if (audioRef.current && !audioRef.current.paused && !isMutedRef.current) {
                  audioRef.current.load();
                  audioRef.current.play().catch(err => {
                    console.error('[ConversationPanel] Failed to resume after stall:', err);
                  });
                }
              };
              
              // Wait for audio to be ready before playing
              const playAudio = () => {
                // Check if muted (use ref for current value)
                if (isMutedRef.current) {
                  console.log('[ConversationPanel] Audio is muted, skipping playback');
                  setAudioReceived(false);
                  return;
                }
                
                console.log('[ConversationPanel] Attempting to play audio...');
                console.log('[ConversationPanel] Audio duration:', audioRef.current.duration, 'seconds');
                console.log('[ConversationPanel] Audio readyState:', audioRef.current.readyState);
                
                // Add event listeners for tracking
                audioRef.current.addEventListener('ended', handleAudioEnded, { once: true });
                audioRef.current.addEventListener('error', handleAudioError, { once: true });
                audioRef.current.addEventListener('stalled', handleAudioStalled, { once: true });
                
                const playPromise = audioRef.current.play();
                if (playPromise !== undefined) {
                  playPromise
                    .then(() => {
                      console.log('[ConversationPanel] ✓✓✓ Audio playback started successfully ✓✓✓');
                      console.log('[ConversationPanel] Audio duration:', audioRef.current.duration, 'seconds');
                      setAudioReceived(false);
                    })
                    .catch(e => {
                      console.error('[ConversationPanel] ✗ Audio play error:', e);
                      console.error('[ConversationPanel] Error name:', e.name);
                      console.error('[ConversationPanel] Error message:', e.message);
                      // Retry once (only if not muted)
                      if (!isMutedRef.current) {
                        setTimeout(() => {
                          if (audioRef.current && !isMutedRef.current) {
                            audioRef.current.play().catch(err => {
                              console.error('[ConversationPanel] Retry also failed:', err);
                            });
                          }
                        }, 500);
                      }
                    });
                } else {
                  console.warn('[ConversationPanel] play() returned undefined');
                }
              };
              
              // Check if audio is ready
              if (audioRef.current.readyState >= 2) { // HAVE_CURRENT_DATA
                console.log('[ConversationPanel] Audio ready, playing immediately');
                playAudio();
              } else {
                console.log('[ConversationPanel] Waiting for audio to load (readyState:', audioRef.current.readyState, ')');
                audioRef.current.addEventListener('canplay', () => {
                  console.log('[ConversationPanel] Audio can play now');
                  playAudio();
                }, { once: true });
                
                audioRef.current.addEventListener('loadeddata', () => {
                  console.log('[ConversationPanel] Audio data loaded, duration:', audioRef.current.duration);
                }, { once: true });
                
                // Fallback timeout
                setTimeout(() => {
                  if (audioRef.current && audioRef.current.paused && !isMutedRef.current) {
                    console.log('[ConversationPanel] Fallback: attempting to play after timeout');
                    playAudio();
                  }
                }, 1000);
              }
            }, 50);
          } catch (error) {
            console.error('[ConversationPanel] ✗✗✗ Error processing audio ✗✗✗');
            console.error('[ConversationPanel] Error:', error);
            console.error('[ConversationPanel] Error stack:', error.stack);
            setAudioReceived(false);
          }
          break;
        
        case 'tts_status':
          console.log('[ConversationPanel] TTS Status:', data.status, data.message);
          if (data.status === 'generating') {
            setErrorMessage('Generating audio...');
          }
          break;
        
        case 'error':
          const errorMsg = data.message || 'An error occurred';
          if (errorMsg.includes('No speech detected')) {
            setErrorMessage('No speech detected. Please try speaking again.');
            setTimeout(() => setErrorMessage(''), 3000);
          } else {
            console.error('Error:', errorMsg);
            setErrorMessage(errorMsg);
            setTimeout(() => setErrorMessage(''), 5000);
          }
          setIsProcessing(false);
          onCallStatusChange?.('listening');
          break;
        
        default:
          console.warn('Unhandled WebSocket message type:', data.type, data);
          break;
      }
    };
    
    console.log('[ConversationPanel] ===== SETTING UP PRIMARY MESSAGE HANDLER =====');
    console.log('[ConversationPanel] WebSocket object:', ws);
    console.log('[ConversationPanel] WebSocket readyState:', ws.readyState);
    console.log('[ConversationPanel] Current onmessage:', ws.onmessage);
    
    // CRITICAL FIX: Register handler with App.jsx immediately
    // App.jsx will route all messages to this handler
    if (messageHandlerRef) {
      console.log('[ConversationPanel] Registering handler with App.jsx via ref...');
      messageHandlerRef.current = messageHandler;
      console.log('[ConversationPanel] ✓✓✓ Handler registered with App.jsx ✓✓✓');
      console.log('[ConversationPanel] App.jsx will route ALL messages to this handler');
    } else {
      console.warn('[ConversationPanel] ⚠ messageHandlerRef not provided - using direct onmessage');
      // Fallback: set onmessage directly if ref not available
      ws.onmessage = (event) => {
        console.log('[ConversationPanel] 🔵 onmessage called (fallback mode)');
        messageHandler(event);
      };
    }
    
    console.log('[ConversationPanel] ✓✓✓ HANDLER SETUP COMPLETE ✓✓✓');
    console.log('[ConversationPanel] Will receive: llm_response, audio_output, transcription, etc.');
    
    return () => {
      console.log('[ConversationPanel] Cleaning up: Unregistering handler');
      try {
        if (messageHandlerRef) {
          messageHandlerRef.current = null;
          console.log('[ConversationPanel] Handler unregistered from App.jsx');
        }
      } catch (e) {
        console.warn('[ConversationPanel] Cleanup error:', e);
      }
    };
  }, [ws, onCallStatusChange]); // Removed pendingUserMessage from deps - we use functional updates

  useEffect(() => {
    // Scroll to bottom when conversation history updates
    if (conversationHistory.length > 0) {
      setTimeout(() => {
        transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    }
  }, [conversationHistory]);
  
  useEffect(() => {
    // Log when agentResponse changes
    if (agentResponse) {
      console.log('[ConversationPanel] agentResponse state updated:', agentResponse.substring(0, 100) + '...');
      console.log('[ConversationPanel] agentResponse length:', agentResponse.length);
    }
  }, [agentResponse]);
  
  // Keep refs in sync with state
  useEffect(() => {
    transcriptRef.current = transcript;
  }, [transcript]);
  
  useEffect(() => {
    pendingUserMessageRef.current = pendingUserMessage;
  }, [pendingUserMessage]);
  
  useEffect(() => {
    conversationHistoryRef.current = conversationHistory;
  }, [conversationHistory]);
  
  useEffect(() => {
    // Log when transcript changes
    if (transcript) {
      console.log('[ConversationPanel] transcript state updated:', transcript);
    }
  }, [transcript]);
  
  useEffect(() => {
    // Log when conversationHistory changes
    console.log('[ConversationPanel] conversationHistory updated, length:', conversationHistory.length);
    if (conversationHistory.length > 0) {
      console.log('[ConversationPanel] Last message:', conversationHistory[conversationHistory.length - 1]);
    }
  }, [conversationHistory]);
  
  // Ensure audio element is ready
  useEffect(() => {
    if (audioRef.current) {
      console.log('Audio element is ready');
      audioRef.current.addEventListener('error', (e) => {
        console.error('Audio element error:', e);
        console.error('Audio error details:', audioRef.current?.error);
      });
      audioRef.current.addEventListener('loadeddata', () => {
        console.log('Audio data loaded');
      });
      audioRef.current.addEventListener('play', () => {
        console.log('Audio playback started');
      });
    }
    
    // Cleanup: revoke all blob URLs on unmount
    return () => {
      audioQueueRef.current.forEach(chunk => {
        URL.revokeObjectURL(chunk.url);
      });
      if (currentAudioUrlRef.current) {
        URL.revokeObjectURL(currentAudioUrlRef.current);
      }
    };
  }, []);

  const base64ToBlob = (base64, mimeType) => {
    try {
      // Remove data URL prefix if present
      let base64Data = base64;
      if (base64.includes(',')) {
        base64Data = base64.split(',')[1];
      }
      
      const byteCharacters = atob(base64Data);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      return new Blob([byteArray], { type: mimeType });
    } catch (error) {
      console.error('Error in base64ToBlob:', error);
      throw error;
    }
  };

  const handleSendText = () => {
    if (!transcript.trim() || !ws || !isConnected) return;
    
    setIsProcessing(true);
    setPendingUserMessage(transcript);
    setAgentResponse('');
    ws.send(JSON.stringify({
      type: 'text_input',
      text: transcript
    }));
  };

  const handleClearHistory = () => {
    setConversationHistory([]);
    setTranscript('');
    setAgentResponse('');
    setPendingUserMessage('');
    setErrorMessage('');
    if (ws && isConnected) {
      ws.send(JSON.stringify({ type: 'clear_history' }));
    }
  };

  const handleCallToggle = () => {
    if (!isConnected) return;
    if (isInCall) {
      onEndCall?.();
    } else {
      onStartCall?.();
    }
  };

  // Get status label
  const getStatusLabel = () => {
    switch (callStatus) {
      case 'listening':
        return 'Listening...';
      case 'speaking':
        return 'Speaking...';
      case 'processing':
        return 'Processing...';
      case 'idle':
      default:
        return 'Ready';
    }
  };

  const getStatusColor = () => {
    switch (callStatus) {
      case 'listening':
        return '#4CAF50'; // Green
      case 'speaking':
        return '#2196F3'; // Blue
      case 'processing':
        return '#FF9800'; // Orange
      default:
        return '#9E9E9E'; // Gray
    }
  };

  const handleMuteToggle = () => {
    // Toggle playback mute
    setIsMuted(prev => {
      const newMuted = !prev;
      isMutedRef.current = newMuted;
      console.log('[ConversationPanel] Playback mute toggled:', newMuted);
      if (newMuted && audioRef.current) {
        audioRef.current.pause();
      }
      return newMuted;
    });
    
    // Also toggle microphone mute if callback is provided
    if (onToggleMicrophoneMute) {
      onToggleMicrophoneMute();
    }
  };
  
  // Keep ref in sync with state
  useEffect(() => {
    isMutedRef.current = isMuted;
  }, [isMuted]);

  return (
    <div className="conversation-panel">
      <div className="conversation-header">
        <h2>Conversation</h2>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button 
            onClick={handleMuteToggle}
            className={`mute-btn ${isMuted || isMicrophoneMuted ? 'muted' : ''}`}
            title={
              isMuted && isMicrophoneMuted ? 'Unmute audio & microphone' :
              isMuted ? 'Unmute audio playback' :
              isMicrophoneMuted ? 'Unmute microphone' :
              'Mute audio & microphone'
            }
          >
            {isMuted || isMicrophoneMuted ? '🔇' : '🔊'}
          </button>
          <button 
            onClick={handleClearHistory}
            className="clear-btn"
            disabled={conversationHistory.length === 0}
          >
            Clear History
          </button>
        </div>
      </div>
      
      {(isMuted || isMicrophoneMuted) && (
        <div style={{ 
          padding: '8px 12px', 
          background: '#fef3c7', 
          borderRadius: '6px', 
          marginBottom: '12px',
          fontSize: '14px',
          color: '#92400e',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          flexWrap: 'wrap'
        }}>
          <span>🔇</span>
          <span>
            {isMuted && isMicrophoneMuted ? 'Audio & Microphone muted' :
             isMuted ? 'Audio playback muted' :
             'Microphone muted'}
          </span>
        </div>
      )}

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
        {/* Call Status Indicator */}
        {isInCall && (
          <div className="call-status" style={{
            padding: '8px',
            marginBottom: '10px',
            backgroundColor: '#f0f0f0',
            borderRadius: '4px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}>
            <span 
              className="status-dot" 
              style={{
                width: '12px',
                height: '12px',
                borderRadius: '50%',
                backgroundColor: getStatusColor(),
                animation: callStatus === 'listening' ? 'pulse 2s infinite' : 'none'
              }}
            />
            <span style={{ fontSize: '14px', fontWeight: '500' }}>
              {getStatusLabel()}
            </span>
            {callStatus === 'speaking' && silenceDuration > 0 && (
              <span style={{ fontSize: '12px', color: '#666', marginLeft: 'auto' }}>
                Silence: {(silenceDuration / 1000).toFixed(1)}s
              </span>
            )}
          </div>
        )}

        {/* Live Transcription Display */}
        {isInCall && liveTranscript && (
          <div className="live-transcript" style={{
            padding: '10px',
            marginBottom: '10px',
            backgroundColor: '#e3f2fd',
            borderRadius: '4px',
            border: '1px solid #90caf9'
          }}>
            <label style={{ fontSize: '12px', color: '#666', display: 'block', marginBottom: '4px' }}>
              Live Transcription:
            </label>
            <div style={{ fontSize: '14px', color: '#1976d2' }}>
              "{liveTranscript}"
            </div>
          </div>
        )}

        <div className="transcript-display">
          <label>Your Input:</label>
          <div className="transcript-text">
            {transcript || (isInCall ? 'Waiting for speech...' : 'Start a call to begin conversation')}
          </div>
        </div>

        <div className="controls">
          <button
            onClick={handleCallToggle}
            className={`call-btn ${isInCall ? 'in-call' : ''}`}
            disabled={!isConnected}
            style={{
              backgroundColor: isInCall ? '#f44336' : '#4CAF50',
              color: 'white',
              padding: '12px 24px',
              fontSize: '16px',
              fontWeight: 'bold'
            }}
          >
            {isInCall ? '🔴 End Call' : '📞 Start Call'}
          </button>
          
          {!isInCall && (
            <button
              onClick={handleSendText}
              className="send-btn"
              disabled={!transcript.trim() || !isConnected || isProcessing}
            >
              {isProcessing ? 'Processing...' : 'Send Text'}
            </button>
          )}
        </div>

        {errorMessage && (
          <div className="error-message" style={{ 
            padding: '10px', 
            marginTop: '10px', 
            backgroundColor: '#fee', 
            border: '1px solid #fcc', 
            borderRadius: '4px',
            color: '#c33'
          }}>
            {errorMessage}
          </div>
        )}

        <div className="agent-response" style={{ 
          marginTop: '10px', 
          padding: '10px', 
          backgroundColor: agentResponse ? '#e8f5e9' : '#f0f0f0', 
          borderRadius: '4px',
          minHeight: '40px',
          border: agentResponse ? '2px solid #4caf50' : '1px solid #ddd'
        }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Agent Response:</label>
          <div className="response-text" style={{ 
            fontSize: '14px', 
            color: '#333',
            whiteSpace: 'pre-wrap',
            wordWrap: 'break-word',
            minHeight: '20px'
          }}>
            {agentResponse || (isProcessing ? 'Processing...' : 'Waiting for response...')}
          </div>
          {agentResponse && (
            <div style={{ fontSize: '11px', color: '#666', marginTop: '5px' }}>
              ✓ Response received ({agentResponse.length} chars) - Render Key: {renderKey}
            </div>
          )}
        </div>
        
        {/* Debug info */}
        {process.env.NODE_ENV === 'development' && (
          <div style={{ 
            marginTop: '10px', 
            padding: '8px', 
            backgroundColor: '#fff3cd', 
            borderRadius: '4px',
            fontSize: '11px',
            fontFamily: 'monospace',
            border: '2px solid #ffc107'
          }}>
            <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>🔍 DEBUG INFO:</div>
            <div>Transcript: "{transcript || '(empty)'}"</div>
            <div>Agent Response: {agentResponse ? `"${agentResponse.substring(0, 50)}..."` : 'null'}</div>
            <div>Agent Response Length: {agentResponse?.length || 0}</div>
            <div>History Length: {conversationHistory.length}</div>
            <div>Is Processing: {isProcessing ? 'Yes' : 'No'}</div>
            <div>Audio Received: {audioReceived ? 'Yes ✓' : 'No ✗'}</div>
            <div>WebSocket: {ws ? (ws.readyState === WebSocket.OPEN ? 'Connected ✓' : `State: ${ws.readyState}`) : 'Not available ✗'}</div>
            <div>Render Key: {renderKey}</div>
            {conversationHistory.length > 0 && (
              <div style={{ marginTop: '5px', padding: '5px', backgroundColor: '#e8f5e9' }}>
                Last Message: {conversationHistory[conversationHistory.length - 1]?.type} - "{conversationHistory[conversationHistory.length - 1]?.text?.substring(0, 30)}..."
              </div>
            )}
          </div>
        )}

        {audioReceived && (
          <div style={{ 
            padding: '8px', 
            marginTop: '10px', 
            backgroundColor: '#e8f5e9', 
            borderRadius: '4px',
            fontSize: '12px',
            color: '#2e7d32'
          }}>
            🔊 Audio received, playing...
          </div>
        )}
        <div style={{ marginTop: '10px' }}>
          <audio 
            ref={audioRef} 
            controls 
            autoPlay
            style={{ width: '100%' }}
            preload="auto"
            onLoadedData={() => {
              console.log('[ConversationPanel] Audio onLoadedData event fired');
              console.log('[ConversationPanel] Audio duration:', audioRef.current?.duration);
            }}
            onCanPlay={() => {
              console.log('[ConversationPanel] Audio onCanPlay event fired');
            }}
            onPlay={() => {
              console.log('[ConversationPanel] ✓ Audio onPlay event fired - audio is playing!');
            }}
            onError={(e) => {
              console.error('[ConversationPanel] Audio element error event:', e);
              console.error('[ConversationPanel] Audio error code:', audioRef.current?.error?.code);
              console.error('[ConversationPanel] Audio error message:', audioRef.current?.error?.message);
            }}
          />
          {audioReceived && (
            <button
              onClick={() => {
                console.log('[ConversationPanel] Manual play button clicked');
                if (audioRef.current) {
                  audioRef.current.play().catch(e => {
                    console.error('[ConversationPanel] Manual play failed:', e);
                  });
                }
              }}
              style={{
                marginTop: '5px',
                padding: '8px 16px',
                backgroundColor: '#4CAF50',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              🔊 Play Audio (Manual)
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ConversationPanel;

