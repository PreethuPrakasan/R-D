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
        """Initialize TTS engine (try edge-tts first, then Coqui TTS, fallback to pyttsx3)"""
        # Try edge-tts first (fastest, best for Windows, free, requires internet)
        try:
            import edge_tts
            self.tts_engine = edge_tts
            self.tts_type = "edge"
            self.edge_voice = "en-US-AriaNeural"  # Default voice, can be changed
            logger.info("Initialized edge-tts (Microsoft Edge TTS)")
            logger.info("edge-tts is fast (~100-300ms), high quality, and free")
            logger.info("Note: Requires internet connection")
            return
        except ImportError as e:
            logger.debug(f"edge-tts not available: {e}")
            logger.info("edge-tts not installed. Install with: pip install edge-tts")
        except Exception as e:
            logger.warning(f"edge-tts initialization failed: {e}")
        
        # Try Coqui TTS (faster than pyttsx3, but may not be available)
        try:
            from TTS.api import TTS
            self.tts_engine = TTS(model_name=self.voice, progress_bar=False, gpu=False)
            self.tts_type = "coqui"
            logger.info(f"Initialized Coqui TTS with model: {self.voice}")
            logger.info("Coqui TTS is faster and higher quality than pyttsx3")
            return
        except ImportError as e:
            logger.debug(f"Coqui TTS not available: {e}")
        except Exception as e:
            logger.warning(f"Coqui TTS initialization failed: {e}")
        
        # Fallback to pyttsx3 (slowest, but always available)
        try:
            import pyttsx3
            self.tts_engine = pyttsx3.init()
            self.tts_type = "pyttsx3"
            
            # Optimize pyttsx3 settings for better performance
            try:
                # Try to set a faster speech rate (default is usually 200, can go up to 300+)
                rate = self.tts_engine.getProperty('rate')
                self.tts_engine.setProperty('rate', min(rate + 50, 300))  # Increase rate by 50, max 300
                logger.info(f"[TTS] Set speech rate to {self.tts_engine.getProperty('rate')}")
            except Exception as rate_err:
                logger.debug(f"Could not adjust speech rate: {rate_err}")
            
            logger.info("Initialized pyttsx3 TTS")
            logger.info("Note: Coqui TTS is not available. pyttsx3 is slower but functional.")
            logger.info("Coqui TTS may not be compatible with your Python version. pyttsx3 will work fine.")
            
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
        
        logger.info(f"[TTS] Starting synthesis for text: '{text[:100]}...' (length: {len(text)} chars)")
        logger.info(f"[TTS] Using engine type: {self.tts_type}")
        
        # Use temporary file if no output path specified
        if not output_path:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            output_path = temp_file.name
            temp_file.close()
            delete_temp = True
        else:
            delete_temp = False
        
        try:
            logger.info(f"[TTS] Generating audio to file: {output_path}")
            if self.tts_type == "edge":
                # edge-tts (Microsoft Edge TTS) - fastest option
                logger.info("[TTS] Using edge-tts to generate audio...")
                import time
                import asyncio
                start = time.time()
                
                async def generate_edge_audio():
                    # edge-tts outputs MP3 by default, but we need WAV
                    # Save to temp MP3 first, then convert to WAV
                    temp_mp3 = output_path.replace('.wav', '.mp3')
                    communicate = self.tts_engine.Communicate(text=text, voice=self.edge_voice)
                    await communicate.save(temp_mp3)
                    
                    # Convert MP3 to WAV using pydub (if available) or ffmpeg
                    try:
                        from pydub import AudioSegment
                        audio = AudioSegment.from_mp3(temp_mp3)
                        audio.export(output_path, format="wav")
                        os.unlink(temp_mp3)  # Delete temp MP3
                        logger.info("[TTS] Converted MP3 to WAV using pydub")
                    except ImportError:
                        # pydub not available, try ffmpeg directly
                        import subprocess
                        try:
                            subprocess.run(
                                ['ffmpeg', '-i', temp_mp3, '-y', output_path],
                                check=True,
                                capture_output=True,
                                timeout=10
                            )
                            os.unlink(temp_mp3)
                            logger.info("[TTS] Converted MP3 to WAV using ffmpeg")
                        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                            # If conversion fails, just use MP3 (frontend should handle it)
                            logger.warning(f"[TTS] Could not convert MP3 to WAV ({e}), using MP3 format")
                            if os.path.exists(temp_mp3):
                                os.rename(temp_mp3, output_path.replace('.wav', '.mp3'))
                                # Note: We'll read the MP3 file instead
                                return output_path.replace('.wav', '.mp3')
                    except Exception as e:
                        logger.error(f"[TTS] Error converting MP3 to WAV: {e}")
                        # Try to use MP3 if it exists
                        if os.path.exists(temp_mp3):
                            return temp_mp3
                    return output_path
                
                # Run async function
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                actual_output = loop.run_until_complete(generate_edge_audio())
                if actual_output and actual_output != output_path:
                    output_path = actual_output  # Use MP3 if conversion failed
                    logger.info(f"[TTS] Using audio file: {output_path}")
                
                elapsed = time.time() - start
                logger.info(f"[TTS] edge-tts generation completed in {elapsed:.2f} seconds")
                logger.info(f"[TTS] Generation speed: {len(text) / elapsed:.1f} chars/second")
            elif self.tts_type == "coqui":
                # Coqui TTS
                logger.info("[TTS] Using Coqui TTS to generate audio...")
                import time
                start = time.time()
                self.tts_engine.tts_to_file(text=text, file_path=output_path)
                elapsed = time.time() - start
                logger.info(f"[TTS] Coqui TTS generation completed in {elapsed:.2f} seconds")
            elif self.tts_type == "pyttsx3":
                # pyttsx3 - save to file
                logger.info("[TTS] Using pyttsx3 to generate audio...")
                logger.info(f"[TTS] Text length: {len(text)} chars")
                logger.info(f"[TTS] Saving to file: {output_path}")
                import time
                start = time.time()
                
                # Save to file
                self.tts_engine.save_to_file(text, output_path)
                logger.info("[TTS] save_to_file() called, now calling runAndWait()...")
                
                # This is the blocking call that might be slow
                self.tts_engine.runAndWait()
                
                elapsed = time.time() - start
                logger.info(f"[TTS] pyttsx3 generation completed in {elapsed:.2f} seconds")
                logger.info(f"[TTS] Generation speed: {len(text) / elapsed:.1f} chars/second")
            else:
                raise RuntimeError("Unknown TTS type")
            
            # Read audio data
            logger.info(f"[TTS] Reading audio file from: {output_path}")
            with open(output_path, 'rb') as f:
                audio_data = f.read()
            
            logger.info(f"[TTS] Audio data read: {len(audio_data)} bytes")
            
            # Verify it's valid WAV data (starts with RIFF header)
            if len(audio_data) >= 4:
                header = audio_data[:4]
                if header == b'RIFF':
                    logger.info("[TTS] ✓ Valid WAV file detected (RIFF header)")
                else:
                    logger.warning(f"[TTS] ⚠ Audio file doesn't start with RIFF header, got: {header}")
                    # Log first 20 bytes for debugging
                    logger.debug(f"[TTS] First 20 bytes: {audio_data[:20]}")
            else:
                logger.error(f"[TTS] ✗ Audio data too short: {len(audio_data)} bytes")
            
            # Log audio file size info
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                logger.info(f"[TTS] Audio file size: {file_size} bytes")
            
            return audio_data
            
        except Exception as e:
            logger.error(f"[TTS] Error synthesizing speech: {e}", exc_info=True)
            raise
        finally:
            if delete_temp and os.path.exists(output_path):
                try:
                    os.unlink(output_path)
                    logger.debug(f"[TTS] Cleaned up temp file: {output_path}")
                except Exception as cleanup_error:
                    logger.warning(f"[TTS] Failed to cleanup temp file: {cleanup_error}")
    
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

