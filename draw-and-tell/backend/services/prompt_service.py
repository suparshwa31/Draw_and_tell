# backend/services/prompt_service.py

import random

class PromptService:
    """
    A service to generate drawing prompts for the kid's loop.
    MVP version using hardcoded lists.
    """
    def __init__(self):
        self.word_banks = {
            "numbers": ["two", "three", "four", "five"],
            "adjectives": ["big", "small", "happy", "friendly", "silly", "colorful", "magical", 
                         "round", "tall", "long", "funny", "fluffy", "bouncy", "sparkly"],
            "objects": ["suns", "trees", "cats", "dogs", "birds", "cars", "fish", "stars", 
                       "balloons", "flowers", "robots", "dinosaurs", "butterflies", "unicorns", 
                       "rockets", "rainbows", "dragons", "houses", "monsters", "spaceships"],
            "locations": ["in the sky", "on a hill", "next to a house", "under the water",
                         "in a garden", "in space", "in a magical forest", "on the beach",
                         "in a castle", "under a rainbow", "in a secret cave"]
        }
        self.prompt_templates = [
            "Draw {number} {adjective} {object}.",
            "Can you draw {number} {object}?",
            "Draw {number} {object} {location}.",
            "Let's draw {number} {adjective} {object} {location}!",
            "Show me {number} {adjective} {object}!",
            "Create {number} {object} that are {adjective}."
        ]
        print("✅ PromptService initialized for MVP.")

    def generate_drawing_prompt(self) -> str:
        """
        Randomly selects a template and fills it with words from the banks.
        Returns a child-friendly drawing prompt.
        """
        template = random.choice(self.prompt_templates)
        
        prompt_parts = {}
        
        if "{number}" in template:
            prompt_parts["number"] = random.choice(self.word_banks["numbers"])
        
        if "{adjective}" in template:
            prompt_parts["adjective"] = random.choice(self.word_banks["adjectives"])
            
        if "{object}" in template:
            prompt_parts["object"] = random.choice(self.word_banks["objects"])
            
        if "{location}" in template:
            prompt_parts["location"] = random.choice(self.word_banks["locations"])

        return template.format(**prompt_parts)

# Create a single instance of the service to be used by the router
prompt_service = PromptService()