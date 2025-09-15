import pytest
import sys
import os
from unittest.mock import patch, MagicMock
import numpy as np
import io

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.asr_service import ASRService

class TestASRService:
    """Test cases for Automatic Speech Recognition service"""
    
    def setup_method(self):
        """Set up test fixtures"""
        with patch('services.asr_service.whisper.load_model') as mock_load_model:
            # Mock the Whisper model
            mock_model = MagicMock()
            mock_load_model.return_value = mock_model
            
            self.asr_service = ASRService()
    
    def test_initialization(self):
        """Test service initialization"""
        assert self.asr_service is not None
        assert hasattr(self.asr_service, 'model')
    
    @patch('services.asr_service.whisper.load_model')
    def test_initialization_with_model_loading(self, mock_load_model):
        """Test initialization loads the correct model"""
        mock_model = MagicMock()
        mock_load_model.return_value = mock_model
        
        asr_service = ASRService()
        
        mock_load_model.assert_called_once_with("base")
        assert asr_service.model == mock_model
    
    def test_transcribe_audio_success(self):
        """Test successful audio transcription"""
        # Mock audio data
        audio_data = b"fake_audio_data"
        
        # Mock Whisper model transcribe method
        mock_result = {
            "text": "Hello, this is a test transcription",
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Hello, this is a test transcription"}
            ]
        }
        self.asr_service.model.transcribe.return_value = mock_result
        
        # Mock audio loading
        with patch('services.asr_service.io.BytesIO') as mock_bytesio:
            mock_audio = MagicMock()
            mock_audio.read.return_value = np.random.rand(16000 * 3)  # 3 seconds of audio
            mock_bytesio.return_value = mock_audio
            
            transcript, confidence = self.asr_service.transcribe_audio(audio_data)
            
            assert transcript == "Hello, this is a test transcription"
            assert isinstance(confidence, float)
            assert 0.0 <= confidence <= 1.0
    
    def test_transcribe_audio_empty_data(self):
        """Test transcription with empty audio data"""
        audio_data = b""
        
        with pytest.raises(ValueError, match="Audio data is empty"):
            self.asr_service.transcribe_audio(audio_data)
    
    def test_transcribe_audio_none_data(self):
        """Test transcription with None audio data"""
        with pytest.raises(ValueError, match="Audio data is empty"):
            self.asr_service.transcribe_audio(None)
    
    def test_transcribe_audio_short_duration(self):
        """Test transcription with very short audio"""
        audio_data = b"short"
        
        # Mock audio loading to return very short audio
        with patch('services.asr_service.io.BytesIO') as mock_bytesio:
            mock_audio = MagicMock()
            mock_audio.read.return_value = np.random.rand(100)  # Very short audio
            mock_bytesio.return_value = mock_audio
            
            with pytest.raises(ValueError, match="Audio is too short"):
                self.asr_service.transcribe_audio(audio_data)
    
    def test_transcribe_audio_model_error(self):
        """Test transcription when model fails"""
        audio_data = b"fake_audio_data"
        
        # Mock model to raise an exception
        self.asr_service.model.transcribe.side_effect = Exception("Model error")
        
        with patch('services.asr_service.io.BytesIO') as mock_bytesio:
            mock_audio = MagicMock()
            mock_audio.read.return_value = np.random.rand(16000 * 3)
            mock_bytesio.return_value = mock_audio
            
            with pytest.raises(Exception, match="Model error"):
                self.asr_service.transcribe_audio(audio_data)
    
    def test_transcribe_audio_audio_loading_error(self):
        """Test transcription when audio loading fails"""
        audio_data = b"fake_audio_data"
        
        with patch('services.asr_service.io.BytesIO') as mock_bytesio:
            mock_bytesio.side_effect = Exception("Audio loading error")
            
            with pytest.raises(Exception, match="Audio loading error"):
                self.asr_service.transcribe_audio(audio_data)
    
    def test_transcribe_audio_confidence_calculation(self):
        """Test confidence score calculation"""
        audio_data = b"fake_audio_data"
        
        # Mock result with segments having different confidence scores
        mock_result = {
            "text": "Hello world",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello", "avg_logprob": -0.5},
                {"start": 1.0, "end": 2.0, "text": "world", "avg_logprob": -0.3}
            ]
        }
        self.asr_service.model.transcribe.return_value = mock_result
        
        with patch('services.asr_service.io.BytesIO') as mock_bytesio:
            mock_audio = MagicMock()
            mock_audio.read.return_value = np.random.rand(16000 * 3)
            mock_bytesio.return_value = mock_audio
            
            transcript, confidence = self.asr_service.transcribe_audio(audio_data)
            
            # Confidence should be calculated from avg_logprob
            expected_confidence = np.exp(-0.4)  # Average of -0.5 and -0.3
            assert abs(confidence - expected_confidence) < 0.01
    
    def test_transcribe_audio_no_segments(self):
        """Test transcription when no segments are returned"""
        audio_data = b"fake_audio_data"
        
        mock_result = {
            "text": "",
            "segments": []
        }
        self.asr_service.model.transcribe.return_value = mock_result
        
        with patch('services.asr_service.io.BytesIO') as mock_bytesio:
            mock_audio = MagicMock()
            mock_audio.read.return_value = np.random.rand(16000 * 3)
            mock_bytesio.return_value = mock_audio
            
            transcript, confidence = self.asr_service.transcribe_audio(audio_data)
            
            assert transcript == ""
            assert confidence == 0.0
    
    def test_transcribe_audio_missing_avg_logprob(self):
        """Test transcription when segments don't have avg_logprob"""
        audio_data = b"fake_audio_data"
        
        mock_result = {
            "text": "Hello world",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello"},
                {"start": 1.0, "end": 2.0, "text": "world"}
            ]
        }
        self.asr_service.model.transcribe.return_value = mock_result
        
        with patch('services.asr_service.io.BytesIO') as mock_bytesio:
            mock_audio = MagicMock()
            mock_audio.read.return_value = np.random.rand(16000 * 3)
            mock_bytesio.return_value = mock_audio
            
            transcript, confidence = self.asr_service.transcribe_audio(audio_data)
            
            assert transcript == "Hello world"
            assert confidence == 0.0  # Default when no avg_logprob available
    
    def test_transcribe_audio_whisper_parameters(self):
        """Test that Whisper is called with correct parameters"""
        audio_data = b"fake_audio_data"
        
        mock_result = {
            "text": "Test transcription",
            "segments": [{"start": 0.0, "end": 2.0, "text": "Test transcription", "avg_logprob": -0.2}]
        }
        self.asr_service.model.transcribe.return_value = mock_result
        
        with patch('services.asr_service.io.BytesIO') as mock_bytesio:
            mock_audio = MagicMock()
            mock_audio.read.return_value = np.random.rand(16000 * 3)
            mock_bytesio.return_value = mock_audio
            
            self.asr_service.transcribe_audio(audio_data)
            
            # Verify transcribe was called with correct parameters
            self.asr_service.model.transcribe.assert_called_once()
            call_args = self.asr_service.model.transcribe.call_args
            
            # Should be called with audio array and language parameter
            assert len(call_args[0]) == 1  # One positional argument (audio)
            assert call_args[1]["language"] == "en"  # English language
    
    def test_transcribe_audio_different_languages(self):
        """Test transcription with different language settings"""
        # This test would verify that the language parameter is correctly passed
        # In a real implementation, you might want to test different languages
        audio_data = b"fake_audio_data"
        
        mock_result = {
            "text": "Test transcription",
            "segments": [{"start": 0.0, "end": 2.0, "text": "Test transcription", "avg_logprob": -0.2}]
        }
        self.asr_service.model.transcribe.return_value = mock_result
        
        with patch('services.asr_service.io.BytesIO') as mock_bytesio:
            mock_audio = MagicMock()
            mock_audio.read.return_value = np.random.rand(16000 * 3)
            mock_bytesio.return_value = mock_audio
            
            # Test with default language (English)
            self.asr_service.transcribe_audio(audio_data)
            
            call_args = self.asr_service.model.transcribe.call_args
            assert call_args[1]["language"] == "en"
    
    def test_transcribe_audio_audio_format_handling(self):
        """Test that different audio formats are handled correctly"""
        audio_data = b"fake_wav_data"
        
        mock_result = {
            "text": "Test transcription",
            "segments": [{"start": 0.0, "end": 2.0, "text": "Test transcription", "avg_logprob": -0.2}]
        }
        self.asr_service.model.transcribe.return_value = mock_result
        
        with patch('services.asr_service.io.BytesIO') as mock_bytesio:
            mock_audio = MagicMock()
            mock_audio.read.return_value = np.random.rand(16000 * 3)
            mock_bytesio.return_value = mock_audio
            
            transcript, confidence = self.asr_service.transcribe_audio(audio_data)
            
            # Should successfully process the audio
            assert transcript == "Test transcription"
            assert confidence > 0
    
    def test_transcribe_audio_confidence_bounds(self):
        """Test that confidence scores are within expected bounds"""
        audio_data = b"fake_audio_data"
        
        # Test with high confidence
        mock_result_high = {
            "text": "Clear speech",
            "segments": [{"start": 0.0, "end": 2.0, "text": "Clear speech", "avg_logprob": -0.1}]
        }
        self.asr_service.model.transcribe.return_value = mock_result_high
        
        with patch('services.asr_service.io.BytesIO') as mock_bytesio:
            mock_audio = MagicMock()
            mock_audio.read.return_value = np.random.rand(16000 * 3)
            mock_bytesio.return_value = mock_audio
            
            transcript, confidence = self.asr_service.transcribe_audio(audio_data)
            
            assert 0.0 <= confidence <= 1.0
            assert confidence > 0.5  # High confidence from low avg_logprob
        
        # Test with low confidence
        mock_result_low = {
            "text": "Unclear speech",
            "segments": [{"start": 0.0, "end": 2.0, "text": "Unclear speech", "avg_logprob": -2.0}]
        }
        self.asr_service.model.transcribe.return_value = mock_result_low
        
        with patch('services.asr_service.io.BytesIO') as mock_bytesio:
            mock_audio = MagicMock()
            mock_audio.read.return_value = np.random.rand(16000 * 3)
            mock_bytesio.return_value = mock_audio
            
            transcript, confidence = self.asr_service.transcribe_audio(audio_data)
            
            assert 0.0 <= confidence <= 1.0
            assert confidence < 0.5  # Low confidence from high avg_logprob
