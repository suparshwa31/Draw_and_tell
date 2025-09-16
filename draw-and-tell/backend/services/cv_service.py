from transformers import AutoProcessor, AutoModelForVision2Seq
from PIL import Image
import torch
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
        # Load processor and model (BLIP-base)
        self.processor = AutoProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        self.model = AutoModelForVision2Seq.from_pretrained("Salesforce/blip-image-captioning-base")
        
        # Safe fallback questions
        self.safe_questions = [
            "Can you tell me what you drew?",
            "What colors did you use in your drawing?",
            "What's your favorite part of your picture?",
            "Can you describe what you created?",
            "What story does your drawing tell?"
        ]
        
        # Apply optimizations
        self._apply_optimizations()
        
        # Warmup the model
        self._warmup_model()
    
    def _apply_optimizations(self):
        """Apply performance optimizations"""
        try:
            # Set device
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = self.model.to(self.device)
            
            # Enable FP16 for GPU
            if torch.cuda.is_available():
                self.model = self.model.half()
                torch.backends.cudnn.benchmark = True
                torch.backends.cudnn.deterministic = False
                logger.info("🚀 Enabled CUDA + FP16 optimizations")
            
            # Compile model if supported (PyTorch 2.0+)
            if hasattr(torch, 'compile'):
                try:
                    self.model = torch.compile(self.model, mode="default")
                    logger.info("🚀 Compiled CV model with torch.compile")
                except Exception as e:
                    logger.warning(f"Could not compile CV model: {e}")
            
            # Set evaluation mode
            self.model.eval()
            
            # Generation config: greedy decoding, shorter max length
            self.generation_config = {
                "max_length": 20,
                "num_beams": 1,
                "do_sample": False,
                "early_stopping": True
            }
            
            logger.info("✅ CV Service optimizations applied")
        except Exception as e:
            logger.warning(f"Could not apply all CV optimizations: {e}")
    
    def _warmup_model(self):
        """Run a dummy forward pass to warm up model & cuDNN"""
        try:
            dummy_image = torch.randn(1, 3, 224, 224).to(self.device)
            if torch.cuda.is_available():
                dummy_image = dummy_image.half()
            with torch.no_grad():
                _ = self.model.generate(dummy_image, **self.generation_config)
            logger.info("⚡ Model warmup completed")
        except Exception as e:
            logger.warning(f"Model warmup failed: {e}")
    
    def analyze_drawing(self, image_path: str) -> Dict[str, Any]:
        """Analyze drawing and generate caption + kid-friendly question"""
        start_time = time.time()
        try:
            # Load and preprocess image
            raw_image = Image.open(image_path).convert('RGB')
            max_size = 224  # smaller size for faster inference
            if max(raw_image.size) > max_size:
                raw_image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            inputs = self.processor(images=raw_image, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = {k: v.to(self.device).half() for k, v in inputs.items()}
            else:
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate caption
            with torch.no_grad():
                output = self.model.generate(**inputs, **self.generation_config)
            
            caption = self.processor.decode(output[0], skip_special_tokens=True)
            
            # Safety check for caption
            safety_result = safety_service.check_content_safety(caption, "caption")
            if not safety_result.is_safe:
                logger.warning(f"Unsafe caption: {caption}")
                caption = safety_result.sanitized_content
                safety_service.log_safety_event("unsafe_caption", caption, safety_result.violations)
            
            # Generate kid-friendly questions
            questions = self._generate_questions(caption)
            selected_question = questions[0] if questions else random.choice(self.safe_questions)
            
            # Safety check for question
            question_safety = safety_service.check_content_safety(selected_question, "question")
            if not question_safety.is_safe:
                logger.warning(f"Unsafe question: {selected_question}")
                selected_question = question_safety.sanitized_content
                safety_service.log_safety_event("unsafe_question", selected_question, question_safety.violations)
            
            processing_time = (time.time() - start_time) * 1000
            logger.info(f"Generated caption: {caption}")
            logger.info(f"Selected question: {selected_question}")
            logger.info(f"⏱️ CV analysis completed in {processing_time:.0f}ms")
            
            return {
                "caption": caption,
                "question": selected_question,
                "success": True,
                "processing_time_ms": processing_time
            }
        except Exception as e:
            logger.error(f"Error analyzing drawing: {e}")
            return {
                "caption": "a drawing",
                "question": random.choice(self.safe_questions),
                "success": False,
                "error": str(e)
            }
    
    @lru_cache(maxsize=100)
    def _generate_questions(self, caption: str) -> List[str]:
        """Generate 3 kid-friendly questions based on caption"""
        caption_lower = caption.lower()
        
        count_questions = [
            "How many things can you count in your drawing?",
            "Can you count all the objects you drew?",
            "What number of items did you draw?",
            "How many different things do you see in your picture?"
        ]
        
        color_questions = [
            "What colors did you use in your drawing?",
            "Can you tell me about the colors you chose?",
            "What's your favorite color in your picture?",
            "Which colors make you happy in your drawing?"
        ]
        
        size_questions = [
            "Are the things in your drawing big or small?",
            "What's the biggest thing you drew?",
            "What's the smallest thing in your picture?",
            "Can you tell me about the sizes of things you drew?"
        ]
        
        location_questions = [
            "Where are the things in your drawing?",
            "What's happening in your picture?",
            "Can you tell me about the place you drew?",
            "What's the setting of your drawing?"
        ]
        
        # Specific object-based questions
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
            specific_questions = [
                "What's the main thing in your drawing?",
                "Can you tell me what you drew?",
                "What's your favorite part of your picture?",
                "What story does your drawing tell?"
            ]
        
        all_questions = count_questions + color_questions + size_questions + location_questions + specific_questions
        return random.sample(all_questions, min(3, len(all_questions)))
    
    def clear_cache(self):
        self._generate_questions.cache_clear()
        logger.info("🧹 CV question cache cleared")
    
    def get_cache_info(self):
        cache_info = self._generate_questions.cache_info()
        return {
            "hits": cache_info.hits,
            "misses": cache_info.misses,
            "current_size": cache_info.currsize,
            "max_size": cache_info.maxsize
        }
    
    def optimize_memory(self):
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("🧹 CV memory optimized")

# Initialize service
cv_service = CVService()
