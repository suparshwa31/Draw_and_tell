from transformers import AutoProcessor, AutoModelForVision2Seq
from PIL import Image
import torch
from typing import Dict, Any

class CVService:
    def __init__(self):
        # Load model and processor
        self.processor = AutoProcessor.from_pretrained("Salesforce/blip-image-captioning-large")
        self.model = AutoModelForVision2Seq.from_pretrained("Salesforce/blip-image-captioning-large")
        
    def analyze_drawing(self, image_path: str) -> Dict[str, Any]:
        """
        Analyzes a drawing using the BLIP model and generates a kid-friendly question.
        Args:
            image_path: Path to the image file
        Returns:
            Dict containing analysis results and generated question
        """
        try:
            # Load and preprocess image
            raw_image = Image.open(image_path).convert('RGB')
            inputs = self.processor(raw_image, return_tensors="pt")

            # Generate caption
            output = self.model.generate(
                **inputs,
                max_length=50,
                num_beams=5,
                temperature=1.0
            )
            caption = self.processor.decode(output[0], skip_special_tokens=True)

            # Generate kid-friendly questions based on caption
            questions = self._generate_questions(caption)

            return {
                "caption": caption,
                "question": questions[0],  # Return first question for simplicity
                "success": True
            }

        except Exception as e:
            print(f"Error analyzing drawing: {str(e)}")
            return {
                "caption": "",
                "question": "Can you tell me what you drew?",  # Fallback question
                "success": False,
                "error": str(e)
            }

    def _generate_questions(self, caption: str) -> list[str]:
        """
        Generates kid-friendly questions based on the image caption.
        """
        # Simple template-based question generation
        templates = [
            f"I see {caption}! What's your favorite part of your drawing?",
            f"Wow! Can you tell me more about {caption}?",
            f"That looks interesting! Why did you decide to draw {caption}?",
            f"I love how you drew {caption}! What's happening in your picture?"
        ]
        
        return templates[:2]  # Return first two questions

# Initialize service
cv_service = CVService()