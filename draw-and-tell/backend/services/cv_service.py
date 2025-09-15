from transformers import AutoProcessor, AutoModelForVision2Seq
from PIL import Image
import torch
import re
import random
from typing import Dict, Any, List
import logging
import time
from functools import lru_cache

# Import safety service
from backend.services.safety_service import safety_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CVService:
    def __init__(self):
        # Load model and processor with optimizations
        self.processor = AutoProcessor.from_pretrained("Salesforce/blip-image-captioning-large")
        self.model = AutoModelForVision2Seq.from_pretrained("Salesforce/blip-image-captioning-large")
        
        # Apply performance optimizations
        self._apply_optimizations()
        
        # Safe fallback questions
        self.safe_questions = [
            "Can you tell me what you drew?",
            "What colors did you use in your drawing?",
            "What's your favorite part of your picture?",
            "Can you describe what you created?",
            "What story does your drawing tell?"
        ]
        
    def _apply_optimizations(self):
        """Apply performance optimizations to reduce inference time"""
        try:
            # Set device
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = self.model.to(self.device)
            
            # Enable optimizations
            if torch.cuda.is_available():
                torch.backends.cudnn.benchmark = True
                torch.backends.cudnn.deterministic = False
                logger.info("🚀 Enabled CUDA optimizations for CV service")
            
            # Try to compile model for faster inference (PyTorch 2.0+)
            if hasattr(torch, 'compile'):
                try:
                    self.model = torch.compile(self.model, mode="reduce-overhead")
                    logger.info("🚀 Compiled CV model with torch.compile")
                except Exception as e:
                    logger.warning(f"Could not compile CV model: {e}")
            
            # Set model to evaluation mode
            self.model.eval()
            
            # Optimize generation parameters for speed
            self.generation_config = {
                "max_length": 30,  # Reduced from 50
                "num_beams": 3,    # Reduced from 5
                "temperature": 0.8,
                "do_sample": True,
                "repetition_penalty": 1.05,
                "early_stopping": True
            }
            
            logger.info("✅ CV Service optimizations applied")
            
        except Exception as e:
            logger.warning(f"Could not apply all CV optimizations: {e}")
        
    def analyze_drawing(self, image_path: str) -> Dict[str, Any]:
        """
        Analyzes a drawing using the BLIP model and generates a kid-friendly question.
        Includes comprehensive safety checks and COPPA compliance.
        """
        start_time = time.time()
        
        try:
            # Load and preprocess image with optimizations
            raw_image = Image.open(image_path).convert('RGB')
            
            # Resize image if too large (faster processing)
            max_size = 512
            if max(raw_image.size) > max_size:
                raw_image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            inputs = self.processor(images=raw_image, return_tensors="pt")
            inputs = {k: v.to(self.device, non_blocking=True) for k, v in inputs.items()}

            # Generate caption with optimized parameters
            with torch.no_grad():
                output = self.model.generate(**inputs, **self.generation_config)
            
            caption = self.processor.decode(output[0], skip_special_tokens=True)
            
            # Safety check on generated caption
            safety_result = safety_service.check_content_safety(caption, "caption")
            
            if not safety_result.is_safe:
                logger.warning(f"Unsafe caption generated: {caption}")
                caption = safety_result.sanitized_content
                
                # Log safety event
                safety_service.log_safety_event(
                    "unsafe_caption",
                    caption,
                    safety_result.violations
                )

            # Generate kid-friendly questions based on caption
            questions = self._generate_questions(caption)
            selected_question = questions[0] if questions else random.choice(self.safe_questions)
            
            # Safety check on selected question
            question_safety = safety_service.check_content_safety(selected_question, "question")
            
            if not question_safety.is_safe:
                logger.warning(f"Unsafe question generated: {selected_question}")
                selected_question = question_safety.sanitized_content
                
                # Log safety event
                safety_service.log_safety_event(
                    "unsafe_question",
                    selected_question,
                    question_safety.violations
                )
            
            processing_time = (time.time() - start_time) * 1000
            logger.info(f"Generated caption: {caption}")
            logger.info(f"Generated questions: {questions}")
            logger.info(f"Selected question: {selected_question}")
            logger.info(f"⏱️ CV analysis completed in {processing_time:.0f}ms")

            return {
                "caption": caption,
                "question": selected_question,
                "success": True,
                "processing_time_ms": processing_time
            }

        except Exception as e:
            logger.error(f"Error analyzing drawing: {str(e)}")
            return {
                "caption": "a drawing",
                "question": random.choice(self.safe_questions),
                "success": False,
                "error": str(e)
            }

    @lru_cache(maxsize=100)
    def _generate_questions(self, caption: str) -> List[str]:
        """
        Generates kid-friendly questions based on the image caption.
        Questions are designed for ages 5-9 and focus on counting, colors, and simple observations.
        Uses caching to avoid regenerating questions for similar captions.
        """
        # Extract key words from caption for more specific questions
        caption_lower = caption.lower()
        
        # Count-based questions
        count_questions = [
            "How many things can you count in your drawing?",
            "Can you count all the objects you drew?",
            "What number of items did you draw?",
            "How many different things do you see in your picture?"
        ]
        
        # Color-based questions
        color_questions = [
            "What colors did you use in your drawing?",
            "Can you tell me about the colors you chose?",
            "What's your favorite color in your picture?",
            "Which colors make you happy in your drawing?"
        ]
        
        # Size-based questions
        size_questions = [
            "Are the things in your drawing big or small?",
            "What's the biggest thing you drew?",
            "What's the smallest thing in your picture?",
            "Can you tell me about the sizes of things you drew?"
        ]
        
        # Location-based questions
        location_questions = [
            "Where are the things in your drawing?",
            "What's happening in your picture?",
            "Can you tell me about the place you drew?",
            "What's the setting of your drawing?"
        ]
        
        # Specific object questions based on common drawing themes
        if any(word in caption_lower for word in ['car', 'cars', 'vehicle', 'truck', 'bus']):
            specific_questions = [
                "How many cars did you draw?",
                "What color are the cars in your picture?",
                "Where are the cars going?",
                "Can you tell me about the cars you drew?"
            ]
        elif any(word in caption_lower for word in ['tree', 'trees', 'plant', 'flower', 'flowers']):
            specific_questions = [
                "How many trees or flowers did you draw?",
                "What colors are the trees and flowers?",
                "Where are the trees growing?",
                "Can you tell me about the nature in your drawing?"
            ]
        elif any(word in caption_lower for word in ['animal', 'dog', 'cat', 'bird', 'fish', 'butterfly']):
            specific_questions = [
                "How many animals did you draw?",
                "What animals can you see in your picture?",
                "What are the animals doing?",
                "Can you tell me about the animals you drew?"
            ]
        elif any(word in caption_lower for word in ['house', 'building', 'home', 'castle']):
            specific_questions = [
                "How many buildings did you draw?",
                "What kind of house or building is this?",
                "What's around the building?",
                "Can you tell me about the place you drew?"
            ]
        elif any(word in caption_lower for word in ['person', 'people', 'boy', 'girl', 'child']):
            specific_questions = [
                "How many people did you draw?",
                "What are the people doing?",
                "Can you tell me about the people in your picture?",
                "What are the people wearing?"
            ]
        else:
            # Generic questions for other content
            specific_questions = [
                "What's the main thing in your drawing?",
                "Can you tell me what you drew?",
                "What's your favorite part of your picture?",
                "What story does your drawing tell?"
            ]
        
        # Combine all question types
        all_questions = count_questions + color_questions + size_questions + location_questions + specific_questions
        
        # Return 3 random questions
        return random.sample(all_questions, min(3, len(all_questions)))
    
    def clear_cache(self):
        """Clear the question generation cache"""
        self._generate_questions.cache_clear()
        logger.info("🧹 CV question cache cleared")
    
    def get_cache_info(self):
        """Get cache statistics"""
        cache_info = self._generate_questions.cache_info()
        return {
            "hits": cache_info.hits,
            "misses": cache_info.misses,
            "current_size": cache_info.currsize,
            "max_size": cache_info.maxsize
        }
    
    def optimize_memory(self):
        """Optimize memory usage"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("🧹 CV memory optimized")

# Initialize service
cv_service = CVService()