import torch
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
import numpy as np
import io
from typing import Tuple
import soundfile as sf
from pydub import AudioSegment

class ASRService:
    def __init__(self):
        # Load Whisper model and processor
        self.processor = AutoProcessor.from_pretrained("openai/whisper-small")
        self.model = AutoModelForSpeechSeq2Seq.from_pretrained("openai/whisper-small")
        
        # Move model to GPU if available
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.model = self.model.to(self.device)
        
        # Set model to evaluation mode
        self.model.eval()

    def transcribe_audio(self, audio_data: bytes) -> Tuple[str, float]:
        try:
            # Convert whatever the user uploaded (webm/m4a/mp3/ogg) into wav
            with io.BytesIO(audio_data) as audio_bytes:
                audio = AudioSegment.from_file(audio_bytes)  # auto-detect format
                audio = audio.set_frame_rate(16000)  # resample to 16 kHz
                audio = audio.set_channels(1)
                
                wav_io = io.BytesIO()
                audio.export(wav_io, format="wav")
                wav_io.seek(0)
                
                audio_array, sampling_rate = sf.read(wav_io)
                
            # Convert to mono if stereo
            if len(audio_array.shape) > 1:
                audio_array = audio_array.mean(axis=1)
            
            # Process audio - this will handle attention mask automatically
            inputs = self.processor(
                audio_array,
                sampling_rate=sampling_rate,
                return_tensors="pt"
            )
            
            # Move inputs to device
            input_features = inputs.input_features.to(self.device)
            
            # Generate transcription with proper parameters
            with torch.no_grad():
                predicted_ids = self.model.generate(
                    input_features,
                    task="transcribe",
                    language="en",
                    return_dict_in_generate=True,
                    output_scores=True
                )
                
                # Extract the generated token ids
                generated_ids = predicted_ids.sequences
                
                # Decode transcription
                transcription = self.processor.batch_decode(
                    generated_ids,
                    skip_special_tokens=True
                )[0]
                
                # Calculate confidence from generation scores
                if hasattr(predicted_ids, 'scores') and predicted_ids.scores:
                    # Calculate average confidence from the generation scores
                    scores = torch.stack(predicted_ids.scores)  # [seq_len, batch_size, vocab_size]
                    probs = torch.softmax(scores, dim=-1)
                    max_probs = torch.max(probs, dim=-1)[0]  # Get max prob for each step
                    confidence = torch.mean(max_probs).item()
                else:
                    # Fallback: use a simpler confidence calculation
                    # Run forward pass to get logits
                    with torch.no_grad():
                        outputs = self.model.generate(
                            input_features,
                            task="transcribe",
                            language="en",
                            output_scores=True,
                            return_dict_in_generate=True,
                            max_new_tokens=448  # Whisper's max length
                        )
                        if hasattr(outputs, 'scores') and outputs.scores:
                            scores = torch.stack(outputs.scores)
                            probs = torch.softmax(scores, dim=-1)
                            max_probs = torch.max(probs, dim=-1)[0]
                            confidence = torch.mean(max_probs).item()
                        else:
                            confidence = 0.5  # Default fallback
            
            return transcription.strip(), float(confidence)
            
        except Exception as e:
            print(f"Error in transcribe_audio: {str(e)}")
            raise

# Initialize service
asr_service = ASRService()