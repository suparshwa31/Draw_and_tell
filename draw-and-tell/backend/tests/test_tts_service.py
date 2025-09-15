import pytest
import sys
import os
from unittest.mock import patch, MagicMock, mock_open
import numpy as np
import io

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.tts_service import TTSService

class TestTTSService:
    """Test cases for Text-to-Speech service"""
    
    def setup_method(self):
        """Set up test fixtures"""
        with patch('services.tts_service.SpeechT5Processor') as mock_processor, \
             patch('services.tts_service.SpeechT5ForTextToSpeech') as mock_model, \
             patch('services.tts_service.SpeechT5HifiGan') as mock_vocoder, \
             patch('services.tts_service.load_dataset') as mock_dataset:
            
            # Mock the TTS components
            mock_processor.from_pretrained.return_value = MagicMock()
            mock_model.from_pretrained.return_value = MagicMock()
            mock_vocoder.from_pretrained.return_value = MagicMock()
            mock_dataset.return_value = [{"xvector": np.random.rand(512)}]
            
            self.tts_service = TTSService()
    
    def test_initialization(self):
        """Test service initialization"""
        assert self.tts_service is not None
        assert hasattr(self.tts_service, 'processor')
        assert hasattr(self.tts_service, 'model')
        assert hasattr(self.tts_service, 'vocoder')
        assert hasattr(self.tts_service, 'device')
        assert hasattr(self.tts_service, 'speaker_embeddings')
    
    def test_initialization_with_embedding_error(self):
        """Test initialization when speaker embeddings fail to load"""
        with patch('services.tts_service.SpeechT5Processor') as mock_processor, \
             patch('services.tts_service.SpeechT5ForTextToSpeech') as mock_model, \
             patch('services.tts_service.SpeechT5HifiGan') as mock_vocoder, \
             patch('services.tts_service.load_dataset') as mock_dataset:
            
            mock_processor.from_pretrained.return_value = MagicMock()
            mock_model.from_pretrained.return_value = MagicMock()
            mock_vocoder.from_pretrained.return_value = MagicMock()
            mock_dataset.side_effect = Exception("Dataset loading failed")
            
            # Should not raise exception, should use random embeddings
            tts_service = TTSService()
            assert tts_service is not None
            assert tts_service.speaker_embeddings is not None
    
    def test_sanitize_text_safe_content(self):
        """Test text sanitization with safe content"""
        safe_text = "Hello, how are you today?"
        sanitized = self.tts_service._sanitize_text(safe_text)
        
        assert sanitized == safe_text
        assert isinstance(sanitized, str)
    
    def test_sanitize_text_unsafe_content(self):
        """Test text sanitization with unsafe content"""
        unsafe_text = "This is scary and violent content"
        sanitized = self.tts_service._sanitize_text(unsafe_text)
        
        assert sanitized != unsafe_text
        assert "scary" not in sanitized or "funny" in sanitized
        assert "violent" not in sanitized or "play" in sanitized
        assert isinstance(sanitized, str)
    
    def test_sanitize_text_empty_input(self):
        """Test text sanitization with empty input"""
        # Empty string
        sanitized = self.tts_service._sanitize_text("")
        assert sanitized == "Hello there!"
        
        # None input
        sanitized = self.tts_service._sanitize_text(None)
        assert sanitized == "Hello there!"
    
    def test_sanitize_text_special_characters(self):
        """Test text sanitization removes special characters"""
        text_with_special = "Hello! @#$%^&*() world!"
        sanitized = self.tts_service._sanitize_text(text_with_special)
        
        assert "@" not in sanitized
        assert "#" not in sanitized
        assert "$" not in sanitized
        assert "%" not in sanitized
        assert "^" not in sanitized
        assert "&" not in sanitized
        assert "*" not in sanitized
        assert "(" not in sanitized
        assert ")" not in sanitized
        assert "Hello world" in sanitized
    
    def test_sanitize_text_length_limit(self):
        """Test text sanitization enforces length limits"""
        long_text = "A" * 600  # Longer than 500 character limit
        sanitized = self.tts_service._sanitize_text(long_text)
        
        assert len(sanitized) <= 503  # 500 + "..."
        assert sanitized.endswith("...")
    
    @patch('services.tts_service.sf.read')
    def test_validate_audio_output_valid(self, mock_sf_read):
        """Test audio validation with valid audio data"""
        # Mock valid audio data
        mock_sf_read.return_value = (np.random.rand(1000), 16000)
        
        # Create mock audio data
        audio_data = b"fake_wav_data" * 100  # Simulate 1KB+ audio
        
        is_valid = self.tts_service._validate_audio_output(audio_data)
        assert is_valid == True
    
    def test_validate_audio_output_too_short(self):
        """Test audio validation with too short audio"""
        short_audio = b"short"  # Less than 1KB
        is_valid = self.tts_service._validate_audio_output(short_audio)
        assert is_valid == False
    
    def test_validate_audio_output_too_large(self):
        """Test audio validation with too large audio"""
        large_audio = b"x" * (11 * 1024 * 1024)  # 11MB, larger than 10MB limit
        is_valid = self.tts_service._validate_audio_output(large_audio)
        assert is_valid == False
    
    @patch('services.tts_service.sf.read')
    def test_validate_audio_output_wrong_sample_rate(self, mock_sf_read):
        """Test audio validation with wrong sample rate"""
        mock_sf_read.return_value = (np.random.rand(1000), 22050)  # Wrong sample rate
        audio_data = b"fake_wav_data" * 100
        
        is_valid = self.tts_service._validate_audio_output(audio_data)
        assert is_valid == False
    
    @patch('services.tts_service.sf.read')
    def test_validate_audio_output_silent(self, mock_sf_read):
        """Test audio validation with silent audio"""
        mock_sf_read.return_value = (np.zeros(1000), 16000)  # Silent audio
        audio_data = b"fake_wav_data" * 100
        
        is_valid = self.tts_service._validate_audio_output(audio_data)
        assert is_valid == False
    
    @patch('services.tts_service.sf.read')
    def test_validate_audio_output_read_error(self, mock_sf_read):
        """Test audio validation with read error"""
        mock_sf_read.side_effect = Exception("Read error")
        audio_data = b"fake_wav_data" * 100
        
        is_valid = self.tts_service._validate_audio_output(audio_data)
        assert is_valid == False
    
    @patch.object(TTSService, '_sanitize_text')
    @patch.object(TTSService, '_validate_audio_output')
    def test_text_to_speech_success(self, mock_validate, mock_sanitize):
        """Test successful text-to-speech conversion"""
        # Mock sanitization
        mock_sanitize.return_value = "Hello world"
        
        # Mock validation
        mock_validate.return_value = True
        
        # Mock processor
        mock_inputs = {"input_ids": MagicMock()}
        self.tts_service.processor.return_tensors = MagicMock(return_value=mock_inputs)
        
        # Mock model generation
        mock_speech = MagicMock()
        mock_speech.cpu.return_value.numpy.return_value = np.random.rand(1000)
        self.tts_service.model.generate_speech.return_value = mock_speech
        
        # Mock vocoder
        self.tts_service.vocoder = MagicMock()
        
        # Mock sf.write
        with patch('services.tts_service.sf.write') as mock_sf_write:
            with patch('io.BytesIO') as mock_bytesio:
                mock_io = MagicMock()
                mock_io.getvalue.return_value = b"fake_audio_data"
                mock_bytesio.return_value = mock_io
                
                result = self.tts_service.text_to_speech("Hello world")
                
                assert result is not None
                assert isinstance(result, bytes)
                assert result == b"fake_audio_data"
    
    @patch.object(TTSService, '_sanitize_text')
    def test_text_to_speech_empty_text(self, mock_sanitize):
        """Test text-to-speech with empty text"""
        mock_sanitize.return_value = ""
        
        result = self.tts_service.text_to_speech("")
        
        assert result is None
    
    @patch.object(TTSService, '_sanitize_text')
    @patch.object(TTSService, '_validate_audio_output')
    def test_text_to_speech_validation_failure(self, mock_validate, mock_sanitize):
        """Test text-to-speech with validation failure"""
        mock_sanitize.return_value = "Hello world"
        mock_validate.return_value = False
        
        # Mock processor and model
        mock_inputs = {"input_ids": MagicMock()}
        self.tts_service.processor.return_tensors = MagicMock(return_value=mock_inputs)
        
        mock_speech = MagicMock()
        mock_speech.cpu.return_value.numpy.return_value = np.random.rand(1000)
        self.tts_service.model.generate_speech.return_value = mock_speech
        
        with patch('services.tts_service.sf.write'):
            with patch('io.BytesIO') as mock_bytesio:
                mock_io = MagicMock()
                mock_io.getvalue.return_value = b"fake_audio_data"
                mock_bytesio.return_value = mock_io
                
                result = self.tts_service.text_to_speech("Hello world")
                
                assert result is None
    
    @patch.object(TTSService, '_sanitize_text')
    @patch.object(TTSService, '_validate_audio_output')
    def test_text_to_speech_nan_values(self, mock_validate, mock_sanitize):
        """Test text-to-speech with NaN values in generated speech"""
        mock_sanitize.return_value = "Hello world"
        mock_validate.return_value = True
        
        # Mock processor
        mock_inputs = {"input_ids": MagicMock()}
        self.tts_service.processor.return_tensors = MagicMock(return_value=mock_inputs)
        
        # Mock model generation with NaN values
        mock_speech = MagicMock()
        nan_array = np.array([np.nan, np.nan, np.nan])
        mock_speech.cpu.return_value.numpy.return_value = nan_array
        self.tts_service.model.generate_speech.return_value = mock_speech
        
        result = self.tts_service.text_to_speech("Hello world")
        
        assert result is None
    
    @patch.object(TTSService, '_sanitize_text')
    @patch.object(TTSService, '_validate_audio_output')
    def test_text_to_speech_zero_amplitude(self, mock_validate, mock_sanitize):
        """Test text-to-speech with zero amplitude audio"""
        mock_sanitize.return_value = "Hello world"
        mock_validate.return_value = True
        
        # Mock processor
        mock_inputs = {"input_ids": MagicMock()}
        self.tts_service.processor.return_tensors = MagicMock(return_value=mock_inputs)
        
        # Mock model generation with zero amplitude
        mock_speech = MagicMock()
        zero_array = np.zeros(1000)
        mock_speech.cpu.return_value.numpy.return_value = zero_array
        self.tts_service.model.generate_speech.return_value = mock_speech
        
        result = self.tts_service.text_to_speech("Hello world")
        
        assert result is None
    
    @patch.object(TTSService, 'text_to_speech')
    def test_generate_question_audio_success(self, mock_text_to_speech):
        """Test successful question audio generation"""
        mock_text_to_speech.return_value = b"fake_audio_data"
        
        result = self.tts_service.generate_question_audio("What colors did you use?")
        
        assert result == b"fake_audio_data"
        mock_text_to_speech.assert_called_once_with("What colors did you use?")
    
    @patch.object(TTSService, 'text_to_speech')
    def test_generate_question_audio_empty_question(self, mock_text_to_speech):
        """Test question audio generation with empty question"""
        result = self.tts_service.generate_question_audio("")
        
        assert result is None
        mock_text_to_speech.assert_not_called()
    
    @patch.object(TTSService, 'text_to_speech')
    def test_generate_question_audio_none_question(self, mock_text_to_speech):
        """Test question audio generation with None question"""
        result = self.tts_service.generate_question_audio(None)
        
        assert result is None
        mock_text_to_speech.assert_not_called()
    
    @patch.object(TTSService, 'text_to_speech')
    def test_generate_response_audio_success(self, mock_text_to_speech):
        """Test successful response audio generation"""
        mock_text_to_speech.return_value = b"fake_audio_data"
        
        result = self.tts_service.generate_response_audio("Great job!")
        
        assert result == b"fake_audio_data"
        mock_text_to_speech.assert_called_once_with("Wow! Great job! That's amazing!")
    
    @patch.object(TTSService, 'text_to_speech')
    def test_generate_response_audio_empty_response(self, mock_text_to_speech):
        """Test response audio generation with empty response"""
        result = self.tts_service.generate_response_audio("")
        
        assert result is None
        mock_text_to_speech.assert_not_called()
    
    @patch.object(TTSService, 'text_to_speech')
    def test_generate_response_audio_none_response(self, mock_text_to_speech):
        """Test response audio generation with None response"""
        result = self.tts_service.generate_response_audio(None)
        
        assert result is None
        mock_text_to_speech.assert_not_called()
    
    def test_safety_integration(self):
        """Test integration with safety service"""
        with patch('services.tts_service.safety_service.check_content_safety') as mock_safety:
            mock_safety.return_value = MagicMock(
                is_safe=False,
                level=MagicMock(),
                violations=["inappropriate_content"],
                sanitized_content="Hello there!"
            )
            
            result = self.tts_service._sanitize_text("unsafe content")
            
            assert result == "Hello there!"
            mock_safety.assert_called_once_with("unsafe content", "tts_text")
    
    def test_device_assignment(self):
        """Test that models are assigned to correct device"""
        # This test verifies that the device assignment logic works
        with patch('services.tts_service.torch.cuda.is_available', return_value=False):
            with patch('services.tts_service.SpeechT5Processor') as mock_processor, \
                 patch('services.tts_service.SpeechT5ForTextToSpeech') as mock_model, \
                 patch('services.tts_service.SpeechT5HifiGan') as mock_vocoder, \
                 patch('services.tts_service.load_dataset') as mock_dataset:
                
                mock_processor.from_pretrained.return_value = MagicMock()
                mock_model.from_pretrained.return_value = MagicMock()
                mock_vocoder.from_pretrained.return_value = MagicMock()
                mock_dataset.return_value = [{"xvector": np.random.rand(512)}]
                
                tts_service = TTSService()
                
                # Verify device is set to CPU when CUDA is not available
                assert tts_service.device == "cpu"
    
    def test_model_eval_mode(self):
        """Test that models are set to evaluation mode"""
        assert self.tts_service.model.eval.called
        assert self.tts_service.vocoder.eval.called
