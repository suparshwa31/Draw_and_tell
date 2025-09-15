# Endpoints: prompt, CV analysis, and STT
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import os
import logging

from backend.services.prompt_service import prompt_service
from backend.services.asr_service import asr_service
from backend.utils.local_storage import local_storage
from backend.services.cv_service import cv_service
from backend.services.tts_service import tts_service
from backend.services.safety_service import safety_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

def generate_response_to_answer(transcript: str, analysis_context: dict) -> str:
    """
    Generate a kid-friendly response based on the child's answer and drawing analysis.
    Includes safety checks and COPPA compliance.
    
    Args:
        transcript: The child's transcribed answer
        analysis_context: The drawing analysis context
        
    Returns:
        str: A kid-friendly response
    """
    # Safety check on transcript first
    safety_result = safety_service.check_content_safety(transcript, "transcript")
    
    if not safety_result.is_safe:
        logger.warning(f"Unsafe transcript detected: {transcript}")
        # Log safety event
        safety_service.log_safety_event(
            "unsafe_transcript",
            transcript,
            safety_result.violations
        )
        # Use sanitized transcript
        transcript = safety_result.sanitized_content
    
    # Simple template-based response generation
    # In a more sophisticated version, this could use an LLM
    
    # Extract key information from analysis
    objects_detected = analysis_context.get('objects_detected', [])
    caption = analysis_context.get('caption', '')
    
    # Generate encouraging responses based on content
    responses = [
        f"That sounds amazing! I love how you described your drawing!",
        f"Wow! You did such a great job explaining your drawing!",
        f"That's so creative! I can tell you put a lot of thought into it!",
        f"Fantastic! Your drawing sounds really special!",
        f"I'm so impressed with your creativity!",
        f"That's wonderful! You're such a talented artist!"
    ]
    
    # Add specific responses based on what they mentioned (safely)
    if any(word in transcript.lower() for word in ['color', 'colors', 'colored']):
        responses.append("I love all the colors you used! They make your drawing so vibrant!")
    
    if any(word in transcript.lower() for word in ['happy', 'fun', 'excited', 'love']):
        responses.append("It sounds like you had so much fun creating this! That makes me happy too!")
    
    if any(word in transcript.lower() for word in ['big', 'small', 'huge', 'tiny']):
        responses.append("The size details you mentioned make your drawing sound really interesting!")
    
    # Return a random response
    import random
    selected_response = random.choice(responses)
    
    # Final safety check on the response
    response_safety = safety_service.check_content_safety(selected_response, "response")
    
    if not response_safety.is_safe:
        logger.warning(f"Unsafe response generated: {selected_response}")
        selected_response = response_safety.sanitized_content
        
        # Log safety event
        safety_service.log_safety_event(
            "unsafe_response",
            selected_response,
            response_safety.violations
        )
    
    return selected_response

class DrawingAnalysis(BaseModel):
    """Analysis results from the CV model"""
    objects_detected: List[str] = Field(default_factory=list, description="List of objects detected in the drawing")
    colors_used: List[str] = Field(default_factory=list, description="List of main colors used in the drawing")
    confidence_score: float = Field(default=0.0, description="Confidence score of the analysis")

class QuestionResponse(BaseModel):
    """Response model for the /analyze-drawing endpoint"""
    question: str = Field(..., description="Follow-up question based on the drawing analysis")
    analysis: DrawingAnalysis = Field(..., description="Analysis results from the CV model")
    drawingId: Optional[str] = None
    questionId: Optional[str] = None
    questionAudio: Optional[str] = Field(None, description="Base64 encoded audio for the question")
    error: Optional[str] = None

class PromptResponse(BaseModel):
    """Response model for the /prompt endpoint"""
    prompt: str = Field(..., description="Drawing prompt for the child")
    error: Optional[str] = None

class TranscriptionResponse(BaseModel):
    """Response model for the /transcribe-answer endpoint"""
    transcript: str = Field(..., description="Transcribed text from the audio recording")
    confidence: float = Field(..., description="Confidence score of the transcription")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    response: Optional[str] = Field(None, description="Generated response to the child's answer")
    responseAudio: Optional[bytes] = Field(None, description="TTS audio for the response")
    error: Optional[str] = None

@router.get("/prompt", response_model=PromptResponse)
async def get_prompt():
    """
    Generates and returns a new drawing prompt for the child.
    Prompts are age-appropriate and designed to encourage creativity.
    
    Returns:
        PromptResponse: A JSON object containing the drawing prompt
        or error message if generation fails.
    """
    try:
        # Generate a new drawing prompt
        new_prompt = prompt_service.generate_drawing_prompt()
        
        # Log the prompt generation
        print(f"Generated new prompt: {new_prompt}")
        
        # Return response
        return PromptResponse(prompt=new_prompt)
        
    except Exception as e:
        print(f"Error generating prompt: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate prompt: {str(e)}"
        )

@router.post('/analyze-drawing', response_model=QuestionResponse)
async def analyze_drawing(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    prompt: str = Form(...)
):
    try:
        # Safety check on prompt
        prompt_safety = safety_service.check_content_safety(prompt, "prompt")
        if not prompt_safety.is_safe:
            logger.warning(f"Unsafe prompt detected: {prompt}")
            safety_service.log_safety_event(
                "unsafe_prompt",
                prompt,
                prompt_safety.violations
            )
            prompt = prompt_safety.sanitized_content

        # Read image
        image_data = await image.read()
        temp_path = f"/tmp/drawing_{image.filename}"
        with open(temp_path, "wb") as buffer:
            buffer.write(image_data)

        result = cv_service.analyze_drawing(temp_path)
        os.remove(temp_path)

        if not result["success"]:
            raise Exception(result.get("error", "Failed to analyze image"))

        analysis = DrawingAnalysis(
            objects_detected=[result["caption"]],
            colors_used=[],
            confidence_score=1.0
        )

        session_id = local_storage.create_session(prompt)

        # Save drawing with COPPA compliance check
        drawing_data = {
            "session_id": session_id,
            "image_data": image_data,
            "caption": result["caption"],
            "analysis": {
                "caption": result["caption"],
                "objects_detected": [result["caption"]],
                "colors_used": [],
                "confidence_score": 1.0
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Validate data collection for COPPA compliance
        is_compliant, violations = safety_service.validate_data_collection(drawing_data)
        if not is_compliant:
            logger.warning(f"COPPA compliance violations: {violations}")
            safety_service.log_safety_event(
                "coppa_violation",
                str(drawing_data),
                violations
            )

        drawing_id = local_storage.save_drawing(
            session_id=session_id,
            image_data=image_data,
            caption=result["caption"],
            analysis={
                "caption": result["caption"],
                "objects_detected": [result["caption"]],
                "colors_used": [],
                "confidence_score": 1.0
            }
        )

        # Generate TTS audio for the question
        try:
            question_audio = tts_service.generate_question_audio(result["question"])
        except Exception as e:
            logger.error(f"Error generating question audio: {str(e)}")
            question_audio = None

        # Save the generated question
        question_id = local_storage.save_response(
            drawing_id=drawing_id,
            question=result["question"],
            question_audio=question_audio
        )

        # Convert audio to base64 for JSON response
        question_audio_b64 = None
        if question_audio:
            import base64
            question_audio_b64 = base64.b64encode(question_audio).decode('utf-8')

        # ✅ Return IDs along with question for frontend
        logger.info(f"Returning question to frontend: {result['question']}")
        return {
            "question": result["question"],
            "drawingId": str(drawing_id),
            "questionId": str(question_id),
            "analysis": analysis,
            "questionAudio": question_audio_b64
        }

    except Exception as e:
        logger.error(f"Error analyzing drawing: {str(e)}")
        return {
            "question": "Can you tell me about what you drew?",
            "drawingId": None,
            "questionId": None,
            "analysis": DrawingAnalysis(),
            "error": str(e)
        }

@router.post('/transcribe-answer', response_model=TranscriptionResponse)
async def transcribe_answer(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    drawing_id: int = Form(...),
    question_id: int = Form(...)
):
    """
    Transcribes the child's recorded audio answer using the Whisper model.
    Saves both the audio and transcript in the local database.
    Includes comprehensive safety checks and COPPA compliance.
    """
    try:
        # Read the audio file
        audio_data = await audio.read()
        
        # Validate audio format
        if not audio.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="File must be an audio recording")
        
        # Check audio file size for COPPA compliance (max 10MB)
        if len(audio_data) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Audio file too large")
            
        # ✅ Use the instance here
        transcript, confidence = asr_service.transcribe_audio(audio_data)
        
        # Safety check on transcript
        transcript_safety = safety_service.check_content_safety(transcript, "transcript")
        if not transcript_safety.is_safe:
            logger.warning(f"Unsafe transcript detected: {transcript}")
            safety_service.log_safety_event(
                "unsafe_transcript",
                transcript,
                transcript_safety.violations
            )
            transcript = transcript_safety.sanitized_content
        
        # Generate response based on transcript and drawing analysis
        try:
            # Get drawing analysis for context
            drawing_data = local_storage.get_drawing(drawing_id)
            analysis_context = drawing_data.get('analysis', {}) if drawing_data else {}
            
            # Generate response using the CV service or a simple template
            response_text = generate_response_to_answer(transcript, analysis_context)
            
            # Generate TTS audio for the response
            response_audio = tts_service.generate_response_audio(response_text)
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            response_text = "That's wonderful! Thank you for sharing your drawing with me!"
            response_audio = None
        
        # COPPA compliance check for data collection
        answer_data = {
            "drawing_id": drawing_id,
            "question_id": question_id,
            "answer": transcript,
            "answer_audio": audio_data,
            "response": response_text,
            "response_audio": response_audio,
            "timestamp": datetime.now().isoformat()
        }
        
        is_compliant, violations = safety_service.validate_data_collection(answer_data)
        if not is_compliant:
            logger.warning(f"COPPA compliance violations in answer: {violations}")
            safety_service.log_safety_event(
                "coppa_violation_answer",
                str(answer_data),
                violations
            )
        
        # Save answer in database
        def save_answer():
            try:
                local_storage.save_response(
                    drawing_id=drawing_id,
                    question_id=question_id,
                    answer=transcript,
                    answer_audio=audio_data,
                    response=response_text,
                    response_audio=response_audio
                )
            except Exception as e:
                logger.error(f"Error saving answer: {str(e)}")
        
        # Run database save in background
        background_tasks.add_task(save_answer)
        
        # Convert response audio to base64 for JSON response
        response_audio_b64 = None
        if response_audio:
            import base64
            response_audio_b64 = base64.b64encode(response_audio).decode('utf-8')

        return TranscriptionResponse(
            transcript=transcript,
            confidence=confidence,
            timestamp=datetime.now().isoformat(),
            response=response_text,
            responseAudio=response_audio_b64
        )
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        return TranscriptionResponse(
            transcript="",
            confidence=0.0,
            error=str(e)
        )
