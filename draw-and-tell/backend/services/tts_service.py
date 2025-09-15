import torch
import numpy as np
import io
import re
import logging
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
            
            logger.info(f"✅ TTS Service initialized on {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to initialize TTS service: {e}")
            raise

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
        if len(text) > 500:
            text = text[:500] + "..."
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

    def text_to_speech(self, text: str) -> Optional[bytes]:
        """
        Convert text to speech using SpeechT5 models with safety checks.
        
        Args:
            text: The text to convert to speech
            
        Returns:
            bytes: WAV audio data, or None if generation fails
        """
        try:
            # Sanitize input text
            safe_text = self._sanitize_text(text)
            
            if not safe_text:
                logger.warning("No safe text to convert to speech")
                return None
            
            # Preprocess text
            inputs = self.processor(text=safe_text, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate speech with safety parameters
            with torch.no_grad():
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
            
            # Convert to WAV bytes
            wav_io = io.BytesIO()
            sf.write(wav_io, speech, 16000, format='WAV')
            wav_io.seek(0)
            audio_data = wav_io.getvalue()
            
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
        return self.text_to_speech(safe_question)

    def generate_response_audio(self, response: str) -> Optional[bytes]:
        """
        Generate audio for a response with encouraging tone and safety checks.
        """
        if not response:
            return None
            
        # Add encouraging phrases safely
        enhanced_response = f"Wow! {response} That's amazing!"
        safe_response = self._sanitize_text(enhanced_response)
        return self.text_to_speech(safe_response)

# Initialize service
tts_service = TTSService()
