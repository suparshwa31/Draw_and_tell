import torch
import numpy as np
import io
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
from datasets import load_dataset
import soundfile as sf
from typing import Tuple

class TTSService:
    def __init__(self):
        # Load TTS models
        self.processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
        self.model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
        self.vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan")
        
        # Load speaker embeddings for better voice quality
        # embeddings_dataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")
        self.speaker_embeddings = torch.randn(1, 512)
        
        # Move models to GPU if available
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.model = self.model.to(self.device)
        self.vocoder = self.vocoder.to(self.device)
        self.speaker_embeddings = self.speaker_embeddings.to(self.device)
        
        # Set models to evaluation mode
        self.model.eval()
        self.vocoder.eval()
        
        print(f"✅ TTS Service initialized on {self.device}")

    def text_to_speech(self, text: str) -> bytes:
        """
        Convert text to speech using SpeechT5 models.
        
        Args:
            text: The text to convert to speech
            
        Returns:
            bytes: WAV audio data
        """
        try:
            # Preprocess text
            inputs = self.processor(text=text, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate speech
            with torch.no_grad():
                speech = self.model.generate_speech(
                    inputs["input_ids"], 
                    self.speaker_embeddings, 
                    vocoder=self.vocoder
                )
            
            # Convert to numpy array and normalize
            speech = speech.cpu().numpy()
            speech = speech / np.max(np.abs(speech))  # Normalize
            
            # Convert to WAV bytes
            wav_io = io.BytesIO()
            sf.write(wav_io, speech, 16000, format='WAV')
            wav_io.seek(0)
            
            return wav_io.getvalue()
            
        except Exception as e:
            print(f"Error in text_to_speech: {str(e)}")
            raise

    def generate_question_audio(self, question: str) -> bytes:
        """
        Generate audio for a question with kid-friendly tone.
        
        Args:
            question: The question to convert to speech
            
        Returns:
            bytes: WAV audio data
        """
        # Add some kid-friendly emphasis
        enhanced_question = f"{question} Tell me all about it!"
        return self.text_to_speech(enhanced_question)

    def generate_response_audio(self, response: str) -> bytes:
        """
        Generate audio for a response with encouraging tone.
        
        Args:
            response: The response to convert to speech
            
        Returns:
            bytes: WAV audio data
        """
        # Add encouraging phrases
        enhanced_response = f"Wow! {response} That's amazing!"
        return self.text_to_speech(enhanced_response)

# Initialize service
tts_service = TTSService()
