import torch
import numpy as np
import io
import re
import logging
import hashlib
from functools import lru_cache
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
from datasets import load_dataset
import soundfile as sf
from typing import Tuple, Optional

# Import safety service
from backend.services.safety_service import safety_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TTSService:
    def __init__(self):
        try:
            # Load TTS models
            self.processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
            self.model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
            self.vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan")
            
            # Load speaker embeddings for better voice quality
            try:
                embeddings_dataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")
                self.speaker_embeddings = torch.tensor(embeddings_dataset[7306]["xvector"]).unsqueeze(0)
            except Exception as e:
                logger.warning(f"Could not load speaker embeddings: {e}")
                self.speaker_embeddings = torch.randn(1, 512)
            
            # Move models to GPU if available
            self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
            self.model = self.model.to(self.device)
            self.vocoder = self.vocoder.to(self.device)
            self.speaker_embeddings = self.speaker_embeddings.to(self.device)
            
            # Set models to evaluation mode
            self.model.eval()
            self.vocoder.eval()
            
            # Apply performance optimizations
            self._apply_optimizations()
            
            logger.info(f"✅ TTS Service initialized on {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to initialize TTS service: {e}")
            raise

    def _apply_optimizations(self):
        """Apply performance optimizations to reduce latency"""
        try:
            # Enable optimizations for faster inference
            if torch.cuda.is_available():
                torch.backends.cudnn.benchmark = True
                torch.backends.cudnn.deterministic = False
                logger.info("🚀 Enabled CUDA optimizations")
            
            # Try to compile models for faster inference (PyTorch 2.0+)
            if hasattr(torch, 'compile'):
                try:
                    self.model = torch.compile(self.model, mode="reduce-overhead")
                    self.vocoder = torch.compile(self.vocoder, mode="reduce-overhead")
                    logger.info("🚀 Compiled models with torch.compile")
                except Exception as e:
                    logger.warning(f"Could not compile models: {e}")
            
            # Set optimal memory format for GPU
            if self.device != "cpu":
                try:
                    self.model = self.model.to(memory_format=torch.channels_last)
                    self.vocoder = self.vocoder.to(memory_format=torch.channels_last)
                    logger.info("🚀 Optimized memory format")
                except Exception as e:
                    logger.warning(f"Could not optimize memory format: {e}")
            
            # Set maximum text length for faster processing
            self.max_text_length = 200  # Reduced from 500
            
            logger.info("✅ Performance optimizations applied")
            
        except Exception as e:
            logger.warning(f"Could not apply all optimizations: {e}")

    def _get_text_hash(self, text: str) -> str:
        """Generate a hash for text caching"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    @lru_cache(maxsize=50)
    def _cached_tts_generation(self, text_hash: str, text: str) -> bytes:
        """Cached TTS generation for repeated texts"""
        return self._generate_audio_internal(text)

    def _generate_audio_internal(self, text: str) -> Optional[bytes]:
        """Internal audio generation without caching"""
        try:
            # Preprocess text with optimizations
            inputs = self.processor(text=text, return_tensors="pt")
            inputs = {k: v.to(self.device, non_blocking=True) for k, v in inputs.items()}
            
            # Generate speech with optimizations
            with torch.no_grad():
                # Use mixed precision if available on GPU
                if self.device != "cpu" and hasattr(torch.cuda, 'amp'):
                    with torch.cuda.amp.autocast():
                        speech = self.model.generate_speech(
                            inputs["input_ids"], 
                            self.speaker_embeddings, 
                            vocoder=self.vocoder
                        )
                else:
                    speech = self.model.generate_speech(
                        inputs["input_ids"], 
                        self.speaker_embeddings, 
                        vocoder=self.vocoder
                    )
            
            # Convert to numpy array and normalize safely
            speech = speech.cpu().numpy()
            
            # Check for NaN or infinite values
            if np.any(np.isnan(speech)) or np.any(np.isinf(speech)):
                logger.warning("Generated speech contains NaN or infinite values")
                return None
            
            # Normalize audio safely
            max_val = np.max(np.abs(speech))
            if max_val > 0:
                speech = speech / max_val
            else:
                logger.warning("Generated speech has zero amplitude")
                return None
            
            # Convert to WAV bytes with optimized settings
            wav_io = io.BytesIO()
            sf.write(wav_io, speech, 16000, format='WAV', subtype='PCM_16')
            wav_io.seek(0)
            audio_data = wav_io.getvalue()
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Error in internal audio generation: {str(e)}")
            return None

    def _sanitize_text(self, text: str) -> str:
        """Sanitize text input for TTS generation"""
        if not text or not isinstance(text, str):
            return "Hello there!"
        
        # Remove special characters that might cause issues
        text = re.sub(r'[^\w\s\.,!?]', '', text)
        
        # Check for inappropriate content using safety service
        safety_result = safety_service.check_content_safety(text, "tts_text")
        
        if not safety_result.is_safe:
            logger.warning(f"Unsafe text detected in TTS: {text}")
            text = safety_result.sanitized_content
            
            # Log safety event
            safety_service.log_safety_event(
                "unsafe_tts_text",
                text,
                safety_result.violations
            )
        
        # Limit text length to prevent extremely long audio
        max_length = getattr(self, 'max_text_length', 200)
        if len(text) > max_length:
            text = text[:max_length] + "..."
            logger.warning(f"Text truncated for TTS: {len(text)} characters")
        
        return text.strip()

    def _validate_audio_output(self, audio_data: bytes) -> bool:
        """Validate generated audio data"""
        try:
            # Check if audio data is not empty
            if not audio_data or len(audio_data) < 1000:  # Minimum 1KB
                logger.warning("Generated audio too short")
                return False
            
            # Check if audio data is not too large (max 10MB)
            if len(audio_data) > 10 * 1024 * 1024:
                logger.warning("Generated audio too large")
                return False
            
            # Try to read the audio data to validate format
            with io.BytesIO(audio_data) as audio_io:
                data, sample_rate = sf.read(audio_io)
                if sample_rate != 16000:
                    logger.warning(f"Unexpected sample rate: {sample_rate}")
                    return False
                
                # Check for silence (all zeros)
                if np.all(data == 0):
                    logger.warning("Generated audio is silent")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Audio validation failed: {e}")
            return False

    def text_to_speech(self, text: str, text_type: str = "unknown") -> Optional[bytes]:
        """
        Convert text to speech using SpeechT5 models with safety checks.
        
        Args:
            text: The text to convert to speech
            text_type: Type of text ("question" or "response")
            
        Returns:
            bytes: WAV audio data, or None if generation fails
        """
        try:
            # Sanitize input text
            safe_text = self._sanitize_text(text)
            
            if not safe_text:
                logger.warning("No safe text to convert to speech")
                return None
            
            # Check cache first for repeated texts
            text_hash = self._get_text_hash(safe_text)
            cached_audio = self._cached_tts_generation(text_hash, safe_text)
            
            if cached_audio:
                logger.debug(f"Using cached audio for text: {safe_text[:30]}...")
                # Validate cached audio
                if self._validate_audio_output(cached_audio):
                    return cached_audio
                else:
                    logger.warning("Cached audio failed validation, regenerating")
            
            # Generate new audio if not cached or validation failed
            audio_data = self._generate_audio_internal(safe_text)
            
            if not audio_data:
                logger.warning("Failed to generate audio")
                return None
            
            # Validate generated audio
            if not self._validate_audio_output(audio_data):
                logger.warning("Generated audio failed validation")
                return None
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Error in text_to_speech: {str(e)}")
            return None

    def generate_question_audio(self, question: str) -> Optional[bytes]:
        """
        Generate audio for a question with kid-friendly tone and safety checks.
        """
        if not question:
            return None
            
        # Don't add extra text to questions - keep them clean
        safe_question = self._sanitize_text(question)
        return self.text_to_speech(safe_question, text_type="question")

    def generate_response_audio(self, response: str) -> Optional[bytes]:
        """
        Generate audio for a response with encouraging tone and safety checks.
        """
        if not response:
            return None
            
        # Add encouraging phrases safely
        enhanced_response = f"Wow! {response} That's amazing!"
        safe_response = self._sanitize_text(enhanced_response)
        return self.text_to_speech(safe_response, text_type="response")

    def clear_cache(self):
        """Clear the TTS cache to free memory"""
        self._cached_tts_generation.cache_clear()
        logger.info("🧹 TTS cache cleared")

    def get_cache_info(self):
        """Get cache statistics"""
        cache_info = self._cached_tts_generation.cache_info()
        return {
            "hits": cache_info.hits,
            "misses": cache_info.misses,
            "current_size": cache_info.currsize,
            "max_size": cache_info.maxsize
        }

    def optimize_memory(self):
        """Optimize memory usage"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("🧹 Memory optimized")

# Initialize service
tts_service = TTSService()
