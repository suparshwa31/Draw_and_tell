import pytest
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import UploadFile
import io
import json

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from routers.kid_loop import generate_response_to_answer

class TestKidLoopRouter:
    """Test cases for Kid Loop API router"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
    
    def test_generate_response_to_answer_safe_content(self):
        """Test response generation with safe content"""
        transcript = "I drew a red car with blue wheels"
        analysis_context = {
            "caption": "a red car",
            "objects_detected": ["car"],
            "colors_used": ["red", "blue"]
        }
        
        with patch('routers.kid_loop.safety_service.check_content_safety') as mock_safety:
            mock_safety.return_value = MagicMock(
                is_safe=True,
                level=MagicMock(),
                violations=[],
                sanitized_content=transcript
            )
            
            response = generate_response_to_answer(transcript, analysis_context)
            
            assert isinstance(response, str)
            assert len(response) > 0
            assert "amazing" in response.lower() or "wonderful" in response.lower()
    
    def test_generate_response_to_answer_unsafe_content(self):
        """Test response generation with unsafe content"""
        transcript = "I want to fight and hurt someone"
        analysis_context = {"caption": "a drawing"}
        
        with patch('routers.kid_loop.safety_service.check_content_safety') as mock_safety:
            mock_safety.return_value = MagicMock(
                is_safe=False,
                level=MagicMock(),
                violations=["inappropriate_violence"],
                sanitized_content="I want to play and have fun"
            )
            
            with patch('routers.kid_loop.safety_service.log_safety_event') as mock_log:
                response = generate_response_to_answer(transcript, analysis_context)
                
                assert isinstance(response, str)
                assert len(response) > 0
                # Should use sanitized content
                assert "play" in response or "fun" in response
                mock_log.assert_called()
    
    def test_generate_response_to_answer_color_mention(self):
        """Test response generation when colors are mentioned"""
        transcript = "I used red and blue colors"
        analysis_context = {"caption": "a colorful drawing"}
        
        with patch('routers.kid_loop.safety_service.check_content_safety') as mock_safety:
            mock_safety.return_value = MagicMock(
                is_safe=True,
                level=MagicMock(),
                violations=[],
                sanitized_content=transcript
            )
            
            response = generate_response_to_answer(transcript, analysis_context)
            
            assert "color" in response.lower()
    
    def test_generate_response_to_answer_happy_mention(self):
        """Test response generation when happy words are mentioned"""
        transcript = "I had so much fun and I'm excited"
        analysis_context = {"caption": "a happy drawing"}
        
        with patch('routers.kid_loop.safety_service.check_content_safety') as mock_safety:
            mock_safety.return_value = MagicMock(
                is_safe=True,
                level=MagicMock(),
                violations=[],
                sanitized_content=transcript
            )
            
            response = generate_response_to_answer(transcript, analysis_context)
            
            assert "fun" in response.lower() or "happy" in response.lower()
    
    def test_generate_response_to_answer_size_mention(self):
        """Test response generation when size words are mentioned"""
        transcript = "I drew a big house and a small car"
        analysis_context = {"caption": "a house and car"}
        
        with patch('routers.kid_loop.safety_service.check_content_safety') as mock_safety:
            mock_safety.return_value = MagicMock(
                is_safe=True,
                level=MagicMock(),
                violations=[],
                sanitized_content=transcript
            )
            
            response = generate_response_to_answer(transcript, analysis_context)
            
            assert "size" in response.lower() or "big" in response.lower() or "small" in response.lower()
    
    @patch('routers.kid_loop.prompt_service')
    def test_get_prompt_endpoint(self, mock_prompt_service):
        """Test GET /prompt endpoint"""
        mock_prompt_service.generate_drawing_prompt.return_value = "Draw a red car"
        
        response = self.client.get("/prompt")
        
        assert response.status_code == 200
        data = response.json()
        assert "prompt" in data
        assert data["prompt"] == "Draw a red car"
        assert "error" not in data
    
    @patch('routers.kid_loop.prompt_service')
    def test_get_prompt_endpoint_error(self, mock_prompt_service):
        """Test GET /prompt endpoint with error"""
        mock_prompt_service.generate_drawing_prompt.side_effect = Exception("Service error")
        
        response = self.client.get("/prompt")
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Service error" in data["detail"]
    
    @patch('routers.kid_loop.cv_service')
    @patch('routers.kid_loop.local_storage')
    @patch('routers.kid_loop.tts_service')
    @patch('routers.kid_loop.safety_service')
    def test_analyze_drawing_endpoint_success(self, mock_safety, mock_tts, mock_storage, mock_cv):
        """Test POST /analyze-drawing endpoint success"""
        # Mock CV service
        mock_cv.analyze_drawing.return_value = {
            "success": True,
            "caption": "a red car",
            "question": "What colors did you use?"
        }
        
        # Mock safety service
        mock_safety.check_content_safety.return_value = MagicMock(
            is_safe=True,
            level=MagicMock(),
            violations=[],
            sanitized_content="Draw a red car"
        )
        mock_safety.validate_data_collection.return_value = (True, [])
        
        # Mock storage
        mock_storage.create_session.return_value = 1
        mock_storage.save_drawing.return_value = 1
        mock_storage.save_response.return_value = 1
        
        # Mock TTS service
        mock_tts.generate_question_audio.return_value = b"fake_audio_data"
        
        # Create test image file
        image_data = b"fake_image_data"
        files = {"image": ("test.jpg", io.BytesIO(image_data), "image/jpeg")}
        data = {"prompt": "Draw a red car"}
        
        response = self.client.post("/analyze-drawing", files=files, data=data)
        
        assert response.status_code == 200
        response_data = response.json()
        assert "question" in response_data
        assert "drawingId" in response_data
        assert "questionId" in response_data
        assert "analysis" in response_data
        assert response_data["question"] == "What colors did you use?"
    
    @patch('routers.kid_loop.cv_service')
    def test_analyze_drawing_endpoint_cv_error(self, mock_cv):
        """Test POST /analyze-drawing endpoint with CV service error"""
        mock_cv.analyze_drawing.return_value = {
            "success": False,
            "error": "CV processing failed"
        }
        
        image_data = b"fake_image_data"
        files = {"image": ("test.jpg", io.BytesIO(image_data), "image/jpeg")}
        data = {"prompt": "Draw a red car"}
        
        response = self.client.post("/analyze-drawing", files=files, data=data)
        
        assert response.status_code == 200  # Should still return 200 with error in response
        response_data = response.json()
        assert "error" in response_data
        assert response_data["question"] == "Can you tell me about what you drew?"
    
    @patch('routers.kid_loop.asr_service')
    @patch('routers.kid_loop.local_storage')
    @patch('routers.kid_loop.tts_service')
    @patch('routers.kid_loop.safety_service')
    def test_transcribe_answer_endpoint_success(self, mock_safety, mock_tts, mock_storage, mock_asr):
        """Test POST /transcribe-answer endpoint success"""
        # Mock ASR service
        mock_asr.transcribe_audio.return_value = ("I used red and blue colors", 0.95)
        
        # Mock safety service
        mock_safety.check_content_safety.return_value = MagicMock(
            is_safe=True,
            level=MagicMock(),
            violations=[],
            sanitized_content="I used red and blue colors"
        )
        mock_safety.validate_data_collection.return_value = (True, [])
        
        # Mock storage
        mock_storage.get_drawing.return_value = {
            "analysis": {"caption": "a colorful drawing"}
        }
        
        # Mock TTS service
        mock_tts.generate_response_audio.return_value = b"fake_response_audio"
        
        # Create test audio file
        audio_data = b"fake_audio_data"
        files = {"audio": ("test.wav", io.BytesIO(audio_data), "audio/wav")}
        data = {"drawing_id": "1", "question_id": "1"}
        
        response = self.client.post("/transcribe-answer", files=files, data=data)
        
        assert response.status_code == 200
        response_data = response.json()
        assert "transcript" in response_data
        assert "confidence" in response_data
        assert "response" in response_data
        assert "responseAudio" in response_data
        assert response_data["transcript"] == "I used red and blue colors"
        assert response_data["confidence"] == 0.95
    
    def test_transcribe_answer_endpoint_invalid_audio(self):
        """Test POST /transcribe-answer endpoint with invalid audio"""
        # Create test file with wrong content type
        files = {"audio": ("test.txt", io.BytesIO(b"not audio"), "text/plain")}
        data = {"drawing_id": "1", "question_id": "1"}
        
        response = self.client.post("/transcribe-answer", files=files, data=data)
        
        assert response.status_code == 400
        response_data = response.json()
        assert "File must be an audio recording" in response_data["detail"]
    
    def test_transcribe_answer_endpoint_audio_too_large(self):
        """Test POST /transcribe-answer endpoint with audio too large"""
        # Create large audio file (11MB)
        large_audio = b"x" * (11 * 1024 * 1024)
        files = {"audio": ("test.wav", io.BytesIO(large_audio), "audio/wav")}
        data = {"drawing_id": "1", "question_id": "1"}
        
        response = self.client.post("/transcribe-answer", files=files, data=data)
        
        assert response.status_code == 400
        response_data = response.json()
        assert "Audio file too large" in response_data["detail"]
    
    @patch('routers.kid_loop.asr_service')
    def test_transcribe_answer_endpoint_asr_error(self, mock_asr):
        """Test POST /transcribe-answer endpoint with ASR error"""
        mock_asr.transcribe_audio.side_effect = Exception("ASR processing failed")
        
        audio_data = b"fake_audio_data"
        files = {"audio": ("test.wav", io.BytesIO(audio_data), "audio/wav")}
        data = {"drawing_id": "1", "question_id": "1"}
        
        response = self.client.post("/transcribe-answer", files=files, data=data)
        
        assert response.status_code == 200  # Should still return 200 with error in response
        response_data = response.json()
        assert "error" in response_data
        assert response_data["transcript"] == ""
        assert response_data["confidence"] == 0.0
    
    @patch('routers.kid_loop.safety_service')
    def test_analyze_drawing_unsafe_prompt(self, mock_safety):
        """Test analyze drawing with unsafe prompt"""
        mock_safety.check_content_safety.return_value = MagicMock(
            is_safe=False,
            level=MagicMock(),
            violations=["inappropriate_content"],
            sanitized_content="Draw a safe picture"
        )
        mock_safety.log_safety_event = MagicMock()
        
        with patch('routers.kid_loop.cv_service') as mock_cv, \
             patch('routers.kid_loop.local_storage') as mock_storage, \
             patch('routers.kid_loop.tts_service') as mock_tts:
            
            mock_cv.analyze_drawing.return_value = {
                "success": True,
                "caption": "a drawing",
                "question": "What did you draw?"
            }
            mock_storage.create_session.return_value = 1
            mock_storage.save_drawing.return_value = 1
            mock_storage.save_response.return_value = 1
            mock_tts.generate_question_audio.return_value = b"fake_audio"
            
            image_data = b"fake_image_data"
            files = {"image": ("test.jpg", io.BytesIO(image_data), "image/jpeg")}
            data = {"prompt": "Draw something inappropriate"}
            
            response = self.client.post("/analyze-drawing", files=files, data=data)
            
            assert response.status_code == 200
            # Should log safety event
            mock_safety.log_safety_event.assert_called()
    
    @patch('routers.kid_loop.safety_service')
    def test_transcribe_answer_unsafe_transcript(self, mock_safety):
        """Test transcribe answer with unsafe transcript"""
        mock_safety.check_content_safety.return_value = MagicMock(
            is_safe=False,
            level=MagicMock(),
            violations=["inappropriate_content"],
            sanitized_content="I drew a safe picture"
        )
        mock_safety.log_safety_event = MagicMock()
        mock_safety.validate_data_collection.return_value = (True, [])
        
        with patch('routers.kid_loop.asr_service') as mock_asr, \
             patch('routers.kid_loop.local_storage') as mock_storage, \
             patch('routers.kid_loop.tts_service') as mock_tts:
            
            mock_asr.transcribe_audio.return_value = ("I drew something inappropriate", 0.9)
            mock_storage.get_drawing.return_value = {"analysis": {}}
            mock_tts.generate_response_audio.return_value = b"fake_audio"
            
            audio_data = b"fake_audio_data"
            files = {"audio": ("test.wav", io.BytesIO(audio_data), "audio/wav")}
            data = {"drawing_id": "1", "question_id": "1"}
            
            response = self.client.post("/transcribe-answer", files=files, data=data)
            
            assert response.status_code == 200
            response_data = response.json()
            # Should use sanitized transcript
            assert "safe" in response_data["transcript"]
            # Should log safety event
            mock_safety.log_safety_event.assert_called()
    
    def test_analyze_drawing_missing_files(self):
        """Test analyze drawing with missing image file"""
        data = {"prompt": "Draw a car"}
        
        response = self.client.post("/analyze-drawing", data=data)
        
        assert response.status_code == 422  # Validation error
    
    def test_analyze_drawing_missing_prompt(self):
        """Test analyze drawing with missing prompt"""
        image_data = b"fake_image_data"
        files = {"image": ("test.jpg", io.BytesIO(image_data), "image/jpeg")}
        
        response = self.client.post("/analyze-drawing", files=files)
        
        assert response.status_code == 422  # Validation error
    
    def test_transcribe_answer_missing_audio(self):
        """Test transcribe answer with missing audio file"""
        data = {"drawing_id": "1", "question_id": "1"}
        
        response = self.client.post("/transcribe-answer", data=data)
        
        assert response.status_code == 422  # Validation error
    
    def test_transcribe_answer_missing_ids(self):
        """Test transcribe answer with missing drawing/question IDs"""
        audio_data = b"fake_audio_data"
        files = {"audio": ("test.wav", io.BytesIO(audio_data), "audio/wav")}
        
        response = self.client.post("/transcribe-answer", files=files)
        
        assert response.status_code == 422  # Validation error
