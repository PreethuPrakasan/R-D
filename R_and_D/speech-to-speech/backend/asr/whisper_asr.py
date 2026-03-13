"""
Whisper-based Speech Recognition Module using faster-whisper
Provides fast, accurate speech recognition with lower latency than standard Whisper
"""
import logging
import numpy as np
from typing import Optional
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class WhisperASR:
    """Whisper-based ASR for real-time speech recognition using faster-whisper"""
    
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        """
        Initialize Whisper ASR
        
        Args:
            model_size: Model size - "tiny", "base", "small", "medium", "large-v2", "large-v3"
                       Use "tiny" or "base" for fastest inference
            device: "cpu" or "cuda" (if GPU available)
            compute_type: "int8", "int8_float16", "float16", or "float32"
                         Use "int8" for CPU (fastest), "float16" for GPU
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self.sample_rate = 16000  # Whisper uses 16kHz
        
    def load_model(self):
        """Load Whisper model"""
        if self.model is not None:
            return
        
        logger.info(f"Loading Whisper model: {self.model_size} (device: {self.device}, compute: {self.compute_type})")
        try:
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def transcribe_audio(self, audio_data: bytes) -> str:
        """
        Transcribe audio data (non-streaming)
        
        Args:
            audio_data: Raw PCM audio bytes (16-bit, mono, 16kHz)
            
        Returns:
            str: Transcribed text
        """
        if not self.model:
            self.load_model()
        
        try:
            # Convert bytes to numpy array
            # PCM audio is 16-bit signed integers (little-endian)
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Run transcription
            segments, info = self.model.transcribe(
                audio_array,
                beam_size=5,
                language="en",  # Can be None for auto-detection
                task="transcribe",
                vad_filter=True,  # Voice Activity Detection - filters out silence
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            # Collect all segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())
            
            transcript = " ".join(text_parts).strip()
            
            if transcript:
                logger.info(f"Transcribed: '{transcript}' (language: {info.language}, probability: {info.language_probability:.2f})")
            else:
                logger.warning("Whisper returned empty transcription")
            
            return transcript
            
        except Exception as e:
            logger.error(f"Error transcribing audio with Whisper: {e}")
            return ""
    
    def transcribe_audio_stream(self, audio_chunks):
        """
        Transcribe audio in streaming mode (for future use)
        
        Args:
            audio_chunks: Generator or list of audio chunks
            
        Yields:
            str: Partial or final transcriptions
        """
        # For now, collect all chunks and transcribe
        # In the future, could implement true streaming with Whisper
        if not self.model:
            self.load_model()
        
        # Collect all audio data
        all_audio = b""
        for chunk in audio_chunks:
            all_audio += chunk
        
        return self.transcribe_audio(all_audio)



