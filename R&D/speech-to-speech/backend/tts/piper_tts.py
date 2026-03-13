"""
TTS Module - Supports Coqui TTS and pyttsx3 fallback
Provides fast, natural text-to-speech synthesis
"""
import logging
import os
import tempfile
from typing import Optional
import io

logger = logging.getLogger(__name__)


class PiperTTS:
    """TTS for text-to-speech synthesis - uses Coqui TTS or pyttsx3"""
    
    def __init__(self, model_path: Optional[str] = None, voice: str = "tts_models/en/ljspeech/tacotron2-DDC"):
        """
        Initialize TTS
        
        Args:
            model_path: Path to TTS model (for Coqui TTS)
            voice: Voice model name or pyttsx3 voice ID
        """
        self.model_path = model_path
        self.voice = voice
        self.tts_engine = None
        self.tts_type = None
        self._initialize_tts()
        
    def _initialize_tts(self):
        """Initialize TTS engine (try Coqui TTS first, fallback to pyttsx3)"""
        # Try Coqui TTS first
        try:
            from TTS.api import TTS
            self.tts_engine = TTS(model_name=self.voice, progress_bar=False, gpu=False)
            self.tts_type = "coqui"
            logger.info(f"Initialized Coqui TTS with model: {self.voice}")
            return
        except Exception as e:
            logger.warning(f"Coqui TTS not available: {e}")
        
        # Fallback to pyttsx3
        try:
            import pyttsx3
            self.tts_engine = pyttsx3.init()
            self.tts_type = "pyttsx3"
            logger.info("Initialized pyttsx3 TTS (fallback)")
            
            # Set voice properties
            voices = self.tts_engine.getProperty('voices')
            if voices:
                # Try to use a female voice if available
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
                else:
                    self.tts_engine.setProperty('voice', voices[0].id)
            
            self.tts_engine.setProperty('rate', 150)  # Speed
            self.tts_engine.setProperty('volume', 0.9)  # Volume
            
        except Exception as e:
            logger.error(f"Failed to initialize TTS: {e}")
            raise RuntimeError("No TTS engine available. Please install TTS or pyttsx3")
    
    def synthesize(self, text: str, output_path: Optional[str] = None) -> bytes:
        """
        Synthesize speech from text
        
        Args:
            text: Text to synthesize
            output_path: Optional path to save audio file
            
        Returns:
            bytes: Audio data (WAV format)
        """
        if not self.tts_engine:
            raise RuntimeError("TTS engine not initialized")
        
        # Use temporary file if no output path specified
        if not output_path:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            output_path = temp_file.name
            temp_file.close()
            delete_temp = True
        else:
            delete_temp = False
        
        try:
            if self.tts_type == "coqui":
                # Coqui TTS
                self.tts_engine.tts_to_file(text=text, file_path=output_path)
            elif self.tts_type == "pyttsx3":
                # pyttsx3 - save to file
                self.tts_engine.save_to_file(text, output_path)
                self.tts_engine.runAndWait()
            else:
                raise RuntimeError("Unknown TTS type")
            
            # Read audio data
            with open(output_path, 'rb') as f:
                audio_data = f.read()
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            raise
        finally:
            if delete_temp and os.path.exists(output_path):
                try:
                    os.unlink(output_path)
                except:
                    pass
    
    def synthesize_stream(self, text: str):
        """
        Synthesize speech with streaming (chunked output)
        
        Args:
            text: Text to synthesize
            
        Yields:
            bytes: Audio chunks
        """
        # For now, synthesize all at once and yield in chunks
        # In production, you might want sentence-level streaming
        audio_data = self.synthesize(text)
        
        # Yield in 4KB chunks
        chunk_size = 4096
        for i in range(0, len(audio_data), chunk_size):
            yield audio_data[i:i + chunk_size]

