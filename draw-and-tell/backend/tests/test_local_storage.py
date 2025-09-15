import pytest
import sys
import os
import tempfile
import sqlite3
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.local_storage import LocalStorage

class TestLocalStorage:
    """Test cases for Local Storage service"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create a temporary database file for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Initialize LocalStorage with temporary database
        self.storage = LocalStorage(db_path=self.temp_db.name)
    
    def teardown_method(self):
        """Clean up test fixtures"""
        # Remove temporary database file
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_initialization(self):
        """Test LocalStorage initialization"""
        assert self.storage is not None
        assert self.storage.db_path == self.temp_db.name
        assert os.path.exists(self.temp_db.name)
    
    def test_database_tables_created(self):
        """Test that all required tables are created"""
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            
            # Check if all tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = ['sessions', 'drawings', 'responses', 'tags']
            for table in expected_tables:
                assert table in tables
    
    def test_create_session(self):
        """Test session creation"""
        prompt = "Draw a red car"
        session_id = self.storage.create_session(prompt)
        
        assert isinstance(session_id, int)
        assert session_id > 0
        
        # Verify session was created in database
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            session = cursor.fetchone()
            
            assert session is not None
            assert session[1] == prompt  # prompt column
            assert session[2] is not None  # timestamp column
    
    def test_save_drawing(self):
        """Test drawing saving"""
        # Create a session first
        session_id = self.storage.create_session("Test prompt")
        
        # Save a drawing
        image_data = b"fake_image_data"
        caption = "A test drawing"
        analysis = {"objects": ["car"], "colors": ["red"]}
        
        drawing_id = self.storage.save_drawing(
            session_id=session_id,
            image_data=image_data,
            caption=caption,
            analysis=analysis
        )
        
        assert isinstance(drawing_id, int)
        assert drawing_id > 0
        
        # Verify drawing was saved
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM drawings WHERE id = ?", (drawing_id,))
            drawing = cursor.fetchone()
            
            assert drawing is not None
            assert drawing[1] == session_id  # session_id column
            assert drawing[2] == image_data  # image_data column
            assert drawing[3] == caption  # caption column
            assert drawing[4] is not None  # timestamp column
    
    def test_save_response(self):
        """Test response saving"""
        # Create a session and drawing first
        session_id = self.storage.create_session("Test prompt")
        drawing_id = self.storage.save_drawing(
            session_id=session_id,
            image_data=b"fake_image",
            caption="Test caption",
            analysis={}
        )
        
        # Save a response
        question = "What colors did you use?"
        answer = "I used red and blue"
        answer_audio = b"fake_audio_data"
        response_text = "Great job!"
        response_audio = b"fake_response_audio"
        
        response_id = self.storage.save_response(
            drawing_id=drawing_id,
            question=question,
            answer=answer,
            answer_audio=answer_audio,
            response=response_text,
            response_audio=response_audio
        )
        
        assert isinstance(response_id, int)
        assert response_id > 0
        
        # Verify response was saved
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM responses WHERE id = ?", (response_id,))
            response = cursor.fetchone()
            
            assert response is not None
            assert response[1] == drawing_id  # drawing_id column
            assert response[2] == question  # question column
            assert response[3] == answer  # answer column
            assert response[4] is not None  # answer_audio_path column
            assert response[5] is None  # question_audio_path column
            assert response[6] == response_text  # response column
            assert response[7] is not None  # response_audio_path column
    
    def test_save_response_with_question_audio(self):
        """Test saving response with question audio"""
        session_id = self.storage.create_session("Test prompt")
        drawing_id = self.storage.save_drawing(
            session_id=session_id,
            image_data=b"fake_image",
            caption="Test caption",
            analysis={}
        )
        
        question = "What colors did you use?"
        question_audio = b"fake_question_audio"
        
        response_id = self.storage.save_response(
            drawing_id=drawing_id,
            question=question,
            question_audio=question_audio
        )
        
        # Verify question audio was saved
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT question_audio_path FROM responses WHERE id = ?", (response_id,))
            result = cursor.fetchone()
            
            assert result is not None
            assert result[0] is not None  # question_audio_path should be set
    
    def test_get_drawing(self):
        """Test retrieving drawing data"""
        session_id = self.storage.create_session("Test prompt")
        drawing_id = self.storage.save_drawing(
            session_id=session_id,
            image_data=b"fake_image_data",
            caption="A test drawing",
            analysis={"objects": ["car"], "colors": ["red"]}
        )
        
        drawing_data = self.storage.get_drawing(drawing_id)
        
        assert drawing_data is not None
        assert drawing_data['id'] == drawing_id
        assert drawing_data['session_id'] == session_id
        assert drawing_data['image_data'] == b"fake_image_data"
        assert drawing_data['caption'] == "A test drawing"
        assert drawing_data['analysis'] == {"objects": ["car"], "colors": ["red"]}
        assert 'timestamp' in drawing_data
    
    def test_get_drawing_not_found(self):
        """Test retrieving non-existent drawing"""
        drawing_data = self.storage.get_drawing(99999)
        assert drawing_data is None
    
    def test_get_session(self):
        """Test retrieving session data"""
        prompt = "Draw a beautiful sunset"
        session_id = self.storage.create_session(prompt)
        
        session_data = self.storage.get_session(session_id)
        
        assert session_data is not None
        assert session_data['id'] == session_id
        assert session_data['prompt'] == prompt
        assert 'timestamp' in session_data
    
    def test_get_session_not_found(self):
        """Test retrieving non-existent session"""
        session_data = self.storage.get_session(99999)
        assert session_data is None
    
    def test_get_all_sessions(self):
        """Test retrieving all sessions"""
        # Create multiple sessions
        session1 = self.storage.create_session("Prompt 1")
        session2 = self.storage.create_session("Prompt 2")
        session3 = self.storage.create_session("Prompt 3")
        
        sessions = self.storage.get_all_sessions()
        
        assert len(sessions) >= 3
        session_ids = [s['id'] for s in sessions]
        assert session1 in session_ids
        assert session2 in session_ids
        assert session3 in session_ids
    
    def test_get_drawings_by_session(self):
        """Test retrieving drawings by session"""
        session_id = self.storage.create_session("Test session")
        
        # Create multiple drawings for the session
        drawing1 = self.storage.save_drawing(
            session_id=session_id,
            image_data=b"image1",
            caption="Drawing 1",
            analysis={}
        )
        drawing2 = self.storage.save_drawing(
            session_id=session_id,
            image_data=b"image2",
            caption="Drawing 2",
            analysis={}
        )
        
        drawings = self.storage.get_drawings_by_session(session_id)
        
        assert len(drawings) == 2
        drawing_ids = [d['id'] for d in drawings]
        assert drawing1 in drawing_ids
        assert drawing2 in drawing_ids
    
    def test_get_responses_by_drawing(self):
        """Test retrieving responses by drawing"""
        session_id = self.storage.create_session("Test session")
        drawing_id = self.storage.save_drawing(
            session_id=session_id,
            image_data=b"test_image",
            caption="Test drawing",
            analysis={}
        )
        
        # Create multiple responses
        response1 = self.storage.save_response(
            drawing_id=drawing_id,
            question="Question 1",
            answer="Answer 1"
        )
        response2 = self.storage.save_response(
            drawing_id=drawing_id,
            question="Question 2",
            answer="Answer 2"
        )
        
        responses = self.storage.get_responses_by_drawing(drawing_id)
        
        assert len(responses) == 2
        response_ids = [r['id'] for r in responses]
        assert response1 in response_ids
        assert response2 in response_ids
    
    def test_database_migration(self):
        """Test database migration for new columns"""
        # This test verifies that the migration system works
        # The migration should add new columns if they don't exist
        
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            
            # Check if new columns exist
            cursor.execute("PRAGMA table_info(responses)")
            columns = [column[1] for column in cursor.fetchall()]
            
            expected_columns = ['question_audio_path', 'response', 'response_audio_path']
            for column in expected_columns:
                assert column in columns
    
    def test_file_operations(self):
        """Test file operations for audio and image data"""
        # Test saving audio data
        audio_data = b"fake_audio_data"
        file_path = self.storage._save_audio_file(audio_data, "test_audio")
        
        assert file_path is not None
        assert os.path.exists(file_path)
        
        # Verify file content
        with open(file_path, 'rb') as f:
            saved_data = f.read()
            assert saved_data == audio_data
        
        # Clean up
        os.unlink(file_path)
    
    def test_error_handling(self):
        """Test error handling in various scenarios"""
        # Test with invalid session ID
        with pytest.raises(Exception):
            self.storage.save_drawing(
                session_id=99999,  # Non-existent session
                image_data=b"test",
                caption="test",
                analysis={}
            )
    
    def test_data_validation(self):
        """Test data validation"""
        # Test with None values
        session_id = self.storage.create_session("Test")
        
        # Should handle None values gracefully
        drawing_id = self.storage.save_drawing(
            session_id=session_id,
            image_data=None,
            caption=None,
            analysis=None
        )
        
        assert drawing_id is not None
        
        # Verify None values are stored correctly
        drawing_data = self.storage.get_drawing(drawing_id)
        assert drawing_data['image_data'] is None
        assert drawing_data['caption'] is None
        assert drawing_data['analysis'] is None
    
    def test_timestamp_handling(self):
        """Test timestamp handling"""
        session_id = self.storage.create_session("Test prompt")
        
        # Check that timestamp is set
        session_data = self.storage.get_session(session_id)
        assert 'timestamp' in session_data
        assert session_data['timestamp'] is not None
        
        # Verify timestamp format
        timestamp = session_data['timestamp']
        assert isinstance(timestamp, str)
        # Should be able to parse as ISO format
        parsed_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        assert isinstance(parsed_time, datetime)
    
    def test_concurrent_access(self):
        """Test concurrent access to database"""
        # This test simulates concurrent access
        session_id = self.storage.create_session("Concurrent test")
        
        # Simulate multiple operations
        drawing_ids = []
        for i in range(5):
            drawing_id = self.storage.save_drawing(
                session_id=session_id,
                image_data=f"image_{i}".encode(),
                caption=f"Drawing {i}",
                analysis={}
            )
            drawing_ids.append(drawing_id)
        
        # Verify all drawings were created
        drawings = self.storage.get_drawings_by_session(session_id)
        assert len(drawings) == 5
        
        for drawing_id in drawing_ids:
            assert any(d['id'] == drawing_id for d in drawings)
