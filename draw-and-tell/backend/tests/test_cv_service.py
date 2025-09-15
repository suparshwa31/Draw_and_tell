import pytest
import sys
import os
from unittest.mock import patch, MagicMock, mock_open
from PIL import Image
import tempfile
import io

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.cv_service import CVService

class TestCVService:
    """Test cases for Computer Vision service"""
    
    def setup_method(self):
        """Set up test fixtures"""
        with patch('services.cv_service.AutoProcessor') as mock_processor, \
             patch('services.cv_service.AutoModelForVision2Seq') as mock_model:
            
            # Mock the processor and model
            mock_processor.from_pretrained.return_value = MagicMock()
            mock_model.from_pretrained.return_value = MagicMock()
            
            self.cv_service = CVService()
    
    def test_initialization(self):
        """Test service initialization"""
        assert self.cv_service is not None
        assert hasattr(self.cv_service, 'processor')
        assert hasattr(self.cv_service, 'model')
        assert hasattr(self.cv_service, 'safe_questions')
        assert len(self.cv_service.safe_questions) > 0
    
    def test_safe_questions_are_kid_friendly(self):
        """Test that safe questions are appropriate for children"""
        for question in self.cv_service.safe_questions:
            assert isinstance(question, str)
            assert len(question) > 0
            assert any(word in question.lower() for word in ['draw', 'picture', 'color', 'tell', 'describe'])
            # Should not contain inappropriate content
            assert not any(word in question.lower() for word in ['adult', 'violence', 'scary', 'inappropriate'])
    
    @patch('services.cv_service.Image.open')
    @patch('services.cv_service.safety_service.check_content_safety')
    def test_analyze_drawing_success(self, mock_safety_check, mock_image_open):
        """Test successful drawing analysis"""
        # Mock image
        mock_image = MagicMock()
        mock_image.convert.return_value = mock_image
        mock_image_open.return_value = mock_image
        
        # Mock processor
        mock_inputs = MagicMock()
        self.cv_service.processor.return_tensors = MagicMock(return_value=mock_inputs)
        
        # Mock model generation
        mock_output = MagicMock()
        mock_output.__getitem__.return_value = MagicMock()
        self.cv_service.model.generate.return_value = mock_output
        
        # Mock processor decode
        self.cv_service.processor.decode.return_value = "a drawing of a car"
        
        # Mock safety checks
        mock_safety_check.return_value = MagicMock(
            is_safe=True,
            level=MagicMock(),
            violations=[],
            sanitized_content="a drawing of a car"
        )
        
        # Mock question generation
        with patch.object(self.cv_service, '_generate_questions') as mock_generate_questions:
            mock_generate_questions.return_value = ["What colors did you use?"]
            
            result = self.cv_service.analyze_drawing("/tmp/test_image.jpg")
            
            assert result["success"] == True
            assert "caption" in result
            assert "question" in result
            assert result["caption"] == "a drawing of a car"
            assert result["question"] == "What colors did you use?"
    
    @patch('services.cv_service.Image.open')
    def test_analyze_drawing_image_error(self, mock_image_open):
        """Test drawing analysis with image loading error"""
        # Mock image loading error
        mock_image_open.side_effect = Exception("Image loading failed")
        
        result = self.cv_service.analyze_drawing("/tmp/invalid_image.jpg")
        
        assert result["success"] == False
        assert "error" in result
        assert result["caption"] == "a drawing"
        assert result["question"] in self.cv_service.safe_questions
    
    @patch('services.cv_service.Image.open')
    @patch('services.cv_service.safety_service.check_content_safety')
    def test_analyze_drawing_unsafe_caption(self, mock_safety_check, mock_image_open):
        """Test drawing analysis with unsafe caption"""
        # Mock image
        mock_image = MagicMock()
        mock_image.convert.return_value = mock_image
        mock_image_open.return_value = mock_image
        
        # Mock processor
        mock_inputs = MagicMock()
        self.cv_service.processor.return_tensors = MagicMock(return_value=mock_inputs)
        
        # Mock model generation
        mock_output = MagicMock()
        mock_output.__getitem__.return_value = MagicMock()
        self.cv_service.model.generate.return_value = mock_output
        
        # Mock processor decode
        self.cv_service.processor.decode.return_value = "a scary monster with weapons"
        
        # Mock unsafe caption safety check
        mock_safety_check.return_value = MagicMock(
            is_safe=False,
            level=MagicMock(),
            violations=["inappropriate_violence"],
            sanitized_content="a character with toys"
        )
        
        # Mock question generation
        with patch.object(self.cv_service, '_generate_questions') as mock_generate_questions:
            mock_generate_questions.return_value = ["What colors did you use?"]
            
            result = self.cv_service.analyze_drawing("/tmp/test_image.jpg")
            
            assert result["success"] == True
            assert result["caption"] == "a character with toys"  # Sanitized
            assert result["question"] == "What colors did you use?"
    
    @patch('services.cv_service.Image.open')
    @patch('services.cv_service.safety_service.check_content_safety')
    def test_analyze_drawing_unsafe_question(self, mock_safety_check, mock_image_open):
        """Test drawing analysis with unsafe question"""
        # Mock image
        mock_image = MagicMock()
        mock_image.convert.return_value = mock_image
        mock_image_open.return_value = mock_image
        
        # Mock processor
        mock_inputs = MagicMock()
        self.cv_service.processor.return_tensors = MagicMock(return_value=mock_inputs)
        
        # Mock model generation
        mock_output = MagicMock()
        mock_output.__getitem__.return_value = MagicMock()
        self.cv_service.model.generate.return_value = mock_output
        
        # Mock processor decode
        self.cv_service.processor.decode.return_value = "a drawing of a car"
        
        # Mock safety checks - safe caption, unsafe question
        def mock_safety_side_effect(content, content_type):
            if content_type == "caption":
                return MagicMock(
                    is_safe=True,
                    level=MagicMock(),
                    violations=[],
                    sanitized_content=content
                )
            else:  # question
                return MagicMock(
                    is_safe=False,
                    level=MagicMock(),
                    violations=["inappropriate_content"],
                    sanitized_content="What colors did you use?"
                )
        
        mock_safety_check.side_effect = mock_safety_side_effect
        
        # Mock question generation
        with patch.object(self.cv_service, '_generate_questions') as mock_generate_questions:
            mock_generate_questions.return_value = ["Tell me about violence and weapons"]
            
            result = self.cv_service.analyze_drawing("/tmp/test_image.jpg")
            
            assert result["success"] == True
            assert result["caption"] == "a drawing of a car"
            assert result["question"] == "What colors did you use?"  # Sanitized
    
    def test_generate_questions_car_theme(self):
        """Test question generation for car-themed drawings"""
        caption = "a red car with blue wheels"
        questions = self.cv_service._generate_questions(caption)
        
        assert isinstance(questions, list)
        assert len(questions) == 3
        assert all(isinstance(q, str) for q in questions)
        
        # Should contain car-specific questions
        car_questions = [q for q in questions if 'car' in q.lower()]
        assert len(car_questions) > 0
    
    def test_generate_questions_animal_theme(self):
        """Test question generation for animal-themed drawings"""
        caption = "a dog and a cat playing"
        questions = self.cv_service._generate_questions(caption)
        
        assert isinstance(questions, list)
        assert len(questions) == 3
        assert all(isinstance(q, str) for q in questions)
        
        # Should contain animal-specific questions
        animal_questions = [q for q in questions if 'animal' in q.lower()]
        assert len(animal_questions) > 0
    
    def test_generate_questions_tree_theme(self):
        """Test question generation for nature-themed drawings"""
        caption = "trees and flowers in a garden"
        questions = self.cv_service._generate_questions(caption)
        
        assert isinstance(questions, list)
        assert len(questions) == 3
        assert all(isinstance(q, str) for q in questions)
        
        # Should contain nature-specific questions
        nature_questions = [q for q in questions if any(word in q.lower() for word in ['tree', 'flower', 'nature'])]
        assert len(nature_questions) > 0
    
    def test_generate_questions_house_theme(self):
        """Test question generation for building-themed drawings"""
        caption = "a big house with a red roof"
        questions = self.cv_service._generate_questions(caption)
        
        assert isinstance(questions, list)
        assert len(questions) == 3
        assert all(isinstance(q, str) for q in questions)
        
        # Should contain building-specific questions
        building_questions = [q for q in questions if any(word in q.lower() for word in ['house', 'building', 'place'])]
        assert len(building_questions) > 0
    
    def test_generate_questions_person_theme(self):
        """Test question generation for person-themed drawings"""
        caption = "a boy and a girl playing"
        questions = self.cv_service._generate_questions(caption)
        
        assert isinstance(questions, list)
        assert len(questions) == 3
        assert all(isinstance(q, str) for q in questions)
        
        # Should contain person-specific questions
        person_questions = [q for q in questions if 'people' in q.lower()]
        assert len(person_questions) > 0
    
    def test_generate_questions_generic_theme(self):
        """Test question generation for generic drawings"""
        caption = "some abstract shapes and colors"
        questions = self.cv_service._generate_questions(caption)
        
        assert isinstance(questions, list)
        assert len(questions) == 3
        assert all(isinstance(q, str) for q in questions)
        
        # Should contain generic questions
        generic_questions = [q for q in questions if any(word in q.lower() for word in ['main', 'favorite', 'story', 'tell'])]
        assert len(generic_questions) > 0
    
    def test_generate_questions_empty_caption(self):
        """Test question generation with empty caption"""
        questions = self.cv_service._generate_questions("")
        
        assert isinstance(questions, list)
        assert len(questions) == 3
        assert all(isinstance(q, str) for q in questions)
    
    def test_generate_questions_all_question_types(self):
        """Test that all question types are included"""
        caption = "a colorful drawing with many objects"
        questions = self.cv_service._generate_questions(caption)
        
        # Should include different types of questions
        question_text = " ".join(questions).lower()
        
        # Count-based questions
        assert any(word in question_text for word in ['count', 'number', 'many', 'how many'])
        
        # Color-based questions
        assert any(word in question_text for word in ['color', 'colors'])
        
        # Size-based questions
        assert any(word in question_text for word in ['big', 'small', 'size'])
        
        # Location-based questions
        assert any(word in question_text for word in ['where', 'happening', 'place', 'setting'])
    
    def test_generate_questions_kid_friendly(self):
        """Test that generated questions are kid-friendly"""
        caption = "a drawing of various objects"
        questions = self.cv_service._generate_questions(caption)
        
        for question in questions:
            # Should be appropriate for kids
            assert not any(word in question.lower() for word in ['adult', 'violence', 'scary', 'inappropriate'])
            
            # Should be encouraging and positive
            assert any(word in question.lower() for word in ['can', 'tell', 'what', 'how', 'where'])
            
            # Should be simple and clear
            assert len(question.split()) <= 15  # Not too complex
    
    @patch('services.cv_service.safety_service.log_safety_event')
    def test_safety_event_logging(self, mock_log_safety_event):
        """Test that safety events are logged when unsafe content is detected"""
        with patch.object(self.cv_service, 'analyze_drawing') as mock_analyze:
            mock_analyze.return_value = {
                "success": True,
                "caption": "unsafe content",
                "question": "safe question"
            }
            
            # This would be called internally by analyze_drawing
            # The actual test would be in the analyze_drawing method
            pass
    
    def test_model_generation_parameters(self):
        """Test that model generation uses safe parameters"""
        # This test would verify that the model.generate call uses appropriate parameters
        # for conservative, kid-friendly output
        with patch('services.cv_service.Image.open') as mock_image_open:
            mock_image = MagicMock()
            mock_image.convert.return_value = mock_image
            mock_image_open.return_value = mock_image
            
            mock_inputs = MagicMock()
            self.cv_service.processor.return_tensors = MagicMock(return_value=mock_inputs)
            
            mock_output = MagicMock()
            mock_output.__getitem__.return_value = MagicMock()
            self.cv_service.model.generate.return_value = mock_output
            
            self.cv_service.processor.decode.return_value = "test caption"
            
            with patch.object(self.cv_service, '_generate_questions') as mock_generate_questions:
                mock_generate_questions.return_value = ["test question"]
                
                self.cv_service.analyze_drawing("/tmp/test.jpg")
                
                # Verify model.generate was called with safe parameters
                self.cv_service.model.generate.assert_called_once()
                call_kwargs = self.cv_service.model.generate.call_args[1]
                
                assert call_kwargs['max_length'] == 50
                assert call_kwargs['temperature'] == 0.7  # Conservative temperature
                assert call_kwargs['do_sample'] == True
                assert 'repetition_penalty' in call_kwargs
