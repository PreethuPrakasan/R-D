"""
Vosk-based Speech Recognition Module
Provides streaming ASR capabilities with low latency
"""
import json
import logging
from typing import Optional, Generator
import vosk
import pyaudio

logger = logging.getLogger(__name__)


class VoskASR:
    """Vosk-based ASR for real-time speech recognition"""
    
    def __init__(self, model_path: Optional[str] = None, sample_rate: int = 16000):
        """
        Initialize Vosk ASR
        
        Args:
            model_path: Path to Vosk model directory. If None, attempts to download.
            sample_rate: Audio sample rate (default 16000)
        """
        self.sample_rate = sample_rate
        self.model_path = model_path
        self.model = None
        self.rec = None
        self.audio_stream = None
        self.pyaudio_instance = None
        
    def load_model(self, model_path: Optional[str] = None):
        """Load Vosk model"""
        if model_path:
            self.model_path = model_path
            
        if not self.model_path:
            # Try to use a default model path or download
            import os
            default_path = os.path.join(os.path.dirname(__file__), "..", "models", "vosk", "vosk-model-small-en-us-0.15")
            if os.path.exists(default_path):
                self.model_path = default_path
            else:
                raise FileNotFoundError(
                    "Vosk model not found. Please download a model from https://alphacephei.com/vosk/models "
                    "and place it in backend/models/vosk/ or specify model_path"
                )
        
        logger.info(f"Loading Vosk model from {self.model_path}")
        self.model = vosk.Model(self.model_path)
        self.rec = vosk.KaldiRecognizer(self.model, self.sample_rate)
        self.rec.SetWords(True)
        logger.info("Vosk model loaded successfully")
    
    def start_stream(self) -> Generator[str, None, None]:
        """
        Start streaming audio from microphone and yield transcriptions
        
        Yields:
            str: Transcribed text (partial or final)
        """
        if not self.model:
            self.load_model()
        
        # Initialize PyAudio
        self.pyaudio_instance = pyaudio.PyAudio()
        
        # Open audio stream
        self.audio_stream = self.pyaudio_instance.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=4000
        )
        
        logger.info("Started audio stream")
        
        try:
            while True:
                data = self.audio_stream.read(4000, exception_on_overflow=False)
                
                if self.rec.AcceptWaveform(data):
                    # Final result
                    result = json.loads(self.rec.Result())
                    if result.get('text'):
                        yield result['text']
                else:
                    # Partial result
                    partial = json.loads(self.rec.PartialResult())
                    if partial.get('partial'):
                        yield partial['partial']
        except Exception as e:
            logger.error(f"Error in audio stream: {e}")
            raise
        finally:
            self.stop_stream()
    
    def stop_stream(self):
        """Stop audio stream"""
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            self.audio_stream = None
        
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
            self.pyaudio_instance = None
        
        logger.info("Stopped audio stream")
    
    def transcribe_audio(self, audio_data: bytes) -> str:
        """
        Transcribe audio data (non-streaming)
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            str: Transcribed text
        """
        if not self.model:
            self.load_model()
        
        # Create a new recognizer for this audio chunk to avoid state issues
        rec = vosk.KaldiRecognizer(self.model, self.sample_rate)
        rec.SetWords(True)
        
        # Process the audio
        if rec.AcceptWaveform(audio_data):
            # Final result available
            result = json.loads(rec.Result())
            text = result.get('text', '')
            if text:
                return text
        
        # If no final result, check for partial result
        partial = json.loads(rec.PartialResult())
        partial_text = partial.get('partial', '')
        if partial_text:
            return partial_text
        
        # Force final result if we have audio but no result yet
        # This helps with short audio clips
        final_result = json.loads(rec.FinalResult())
        final_text = final_result.get('text', '')
        return final_text

