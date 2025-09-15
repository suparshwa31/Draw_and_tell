import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import base64
from pathlib import Path

class LocalStorage:
    """
    Manages local storage of drawing sessions, responses, and images using SQLite.
    """
    
    def __init__(self):
        """Initialize the database and create tables if they don't exist."""
        # Ensure data directory exists
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.images_dir = self.data_dir / "images"
        self.db_path = self.data_dir / "draw_and_tell.db"
        
        # Create directories if they don't exist
        self.data_dir.mkdir(exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Create database tables if they don't exist and migrate existing tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    prompt TEXT NOT NULL
                )
            ''')
            
            # Create drawings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS drawings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    image_path TEXT NOT NULL,
                    caption TEXT,
                    analysis TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            ''')
            
            # Create responses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    drawing_id INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT,
                    answer_audio_path TEXT,
                    question_audio_path TEXT,
                    response TEXT,
                    response_audio_path TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (drawing_id) REFERENCES drawings (id)
                )
            ''')
            
            # Create tags table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    drawing_id INTEGER NOT NULL,
                    tag TEXT NOT NULL,
                    FOREIGN KEY (drawing_id) REFERENCES drawings (id)
                )
            ''')
            
            # Migrate existing responses table if needed
            self._migrate_responses_table(cursor)
            
            conn.commit()
    
    def _migrate_responses_table(self, cursor):
        """Migrate existing responses table to include new TTS columns."""
        try:
            # Check if the responses table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='responses'")
            if not cursor.fetchone():
                return  # Table doesn't exist, will be created with new schema
            
            # Get current columns
            cursor.execute("PRAGMA table_info(responses)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Add missing columns
            new_columns = [
                ("question_audio_path", "TEXT"),
                ("response", "TEXT"),
                ("response_audio_path", "TEXT")
            ]
            
            for column_name, column_type in new_columns:
                if column_name not in columns:
                    print(f"🔄 Adding column {column_name} to responses table...")
                    cursor.execute(f"ALTER TABLE responses ADD COLUMN {column_name} {column_type}")
                    print(f"✅ Added column {column_name}")
                else:
                    print(f"✅ Column {column_name} already exists")
                    
        except Exception as e:
            print(f"⚠️  Warning: Could not migrate responses table: {str(e)}")
            # Don't raise the exception, just log it
    
    def create_session(self, prompt: str) -> int:
        """Create a new drawing session."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO sessions (timestamp, prompt) VALUES (?, ?)',
                (datetime.now().isoformat(), prompt)
            )
            conn.commit()
            return cursor.lastrowid
    
    def save_drawing(self, session_id: int, image_data: bytes, caption: str = None, analysis: Dict = None) -> int:
        """
        Save a drawing and its analysis data.
        
        Args:
            session_id: ID of the session
            image_data: Raw image bytes
            caption: Optional caption from CV analysis
            analysis: Optional dictionary of analysis results
        
        Returns:
            ID of the saved drawing
        """
        # Save image file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_filename = f"drawing_{timestamp}.png"
        image_path = self.images_dir / image_filename
        
        with open(image_path, 'wb') as f:
            f.write(image_data)
        
        # Save drawing record
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO drawings 
                (session_id, image_path, caption, analysis, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                session_id,
                str(image_path),
                caption,
                json.dumps(analysis) if analysis else None,
                datetime.now().isoformat()
            ))
            
            drawing_id = cursor.lastrowid
            
            # Save tags if present in analysis
            if analysis and 'objects_detected' in analysis:
                for obj in analysis['objects_detected']:
                    cursor.execute(
                        'INSERT INTO tags (drawing_id, tag) VALUES (?, ?)',
                        (drawing_id, obj)
                    )
            
            conn.commit()
            return drawing_id
    
    def save_response(self, drawing_id: int, question: str = None, question_id: int = None, 
                     answer: str = None, answer_audio: bytes = None, 
                     question_audio: bytes = None, response: str = None, 
                     response_audio: bytes = None) -> int:
        """
        Save or update a question-answer response.
        
        Args:
            drawing_id: ID of the drawing
            question: Question text (for new questions)
            question_id: ID of existing question (for updating answers)
            answer: Optional answer text
            answer_audio: Optional answer audio data
            
        Returns:
            ID of the response record
        """
        # Save audio files if provided
        audio_path = None
        question_audio_path = None
        response_audio_path = None
        
        if answer_audio:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            audio_filename = f"answer_{timestamp}.wav"
            audio_path = self.data_dir / "audio" / audio_filename
            audio_path.parent.mkdir(exist_ok=True)
            
            with open(audio_path, 'wb') as f:
                f.write(answer_audio)
        
        if question_audio:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            audio_filename = f"question_{timestamp}.wav"
            question_audio_path = self.data_dir / "audio" / audio_filename
            question_audio_path.parent.mkdir(exist_ok=True)
            
            with open(question_audio_path, 'wb') as f:
                f.write(question_audio)
        
        if response_audio:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            audio_filename = f"response_{timestamp}.wav"
            response_audio_path = self.data_dir / "audio" / audio_filename
            response_audio_path.parent.mkdir(exist_ok=True)
            
            with open(response_audio_path, 'wb') as f:
                f.write(response_audio)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if question_id:
                # Update existing response with answer
                cursor.execute('''
                    UPDATE responses 
                    SET answer = ?, answer_audio_path = ?, response = ?, response_audio_path = ?, timestamp = ?
                    WHERE id = ? AND drawing_id = ?
                ''', (
                    answer,
                    str(audio_path) if audio_path else None,
                    response,
                    str(response_audio_path) if response_audio_path else None,
                    datetime.now().isoformat(),
                    question_id,
                    drawing_id
                ))
                response_id = question_id
            else:
                # Create new response
                cursor.execute('''
                    INSERT INTO responses 
                    (drawing_id, question, answer, answer_audio_path, question_audio_path, response, response_audio_path, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    drawing_id,
                    question,
                    answer,
                    str(audio_path) if audio_path else None,
                    str(question_audio_path) if question_audio_path else None,
                    response,
                    str(response_audio_path) if response_audio_path else None,
                    datetime.now().isoformat()
                ))
                response_id = cursor.lastrowid
                
            conn.commit()
            return response_id
    
    def get_drawing(self, drawing_id: int) -> Dict[str, Any]:
        """Get drawing data by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, session_id, image_path, caption, analysis, timestamp
                FROM drawings WHERE id = ?
            ''', (drawing_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'session_id': row[1],
                    'image_path': row[2],
                    'caption': row[3],
                    'analysis': json.loads(row[4]) if row[4] else {},
                    'timestamp': row[5]
                }
            return None
    
    def get_session(self, session_id: int) -> Dict[str, Any]:
        """Get complete session data including drawings and responses."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get session data
            cursor.execute('SELECT * FROM sessions WHERE id = ?', (session_id,))
            session = dict(cursor.fetchone())
            
            # Get drawings
            cursor.execute('SELECT * FROM drawings WHERE session_id = ?', (session_id,))
            drawings = [dict(row) for row in cursor.fetchall()]
            
            # For each drawing, get responses and tags
            for drawing in drawings:
                # Get responses
                cursor.execute('SELECT * FROM responses WHERE drawing_id = ?', (drawing['id'],))
                drawing['responses'] = [dict(row) for row in cursor.fetchall()]
                
                # Get tags
                cursor.execute('SELECT tag FROM tags WHERE drawing_id = ?', (drawing['id'],))
                drawing['tags'] = [row[0] for row in cursor.fetchall()]
                
                # Parse analysis JSON
                if drawing['analysis']:
                    drawing['analysis'] = json.loads(drawing['analysis'])
            
            session['drawings'] = drawings
            return session

# Initialize storage
local_storage = LocalStorage()
