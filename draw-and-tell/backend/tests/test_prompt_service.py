import unittest
import sys
import os

# Add the parent directory to Python path to find the backend package
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.services.prompt_service import PromptService

class TestPromptService(unittest.TestCase):
    def setUp(self):
        """Set up a new PromptService instance for each test"""
        self.service = PromptService()

    def test_initialization(self):
        """Test if PromptService initializes with correct word banks and templates"""
        self.assertIsInstance(self.service.word_banks, dict)
        self.assertIsInstance(self.service.prompt_templates, list)
        
        # Check if all required word bank categories exist
        required_categories = ["numbers", "adjectives", "objects", "locations"]
        for category in required_categories:
            self.assertIn(category, self.service.word_banks)
            self.assertGreater(len(self.service.word_banks[category]), 0)

        # Check if templates exist
        self.assertGreater(len(self.service.prompt_templates), 0)

    def test_generate_drawing_prompt_format(self):
        """Test if generated prompts are properly formatted strings"""
        for _ in range(10):  # Test multiple times due to randomization
            prompt = self.service.generate_drawing_prompt()
            
            # Check if prompt is a non-empty string
            self.assertIsInstance(prompt, str)
            self.assertGreater(len(prompt), 0)
            
            # Check if prompt ends with proper punctuation
            self.assertIn(prompt[-1], [".", "?"])
            
            # Check if prompt starts with capital letter
            self.assertTrue(prompt[0].isupper())

    def test_prompt_content_variation(self):
        """Test if prompts show variation in content"""
        prompts = set()
        for _ in range(50):  # Generate multiple prompts
            prompts.add(self.service.generate_drawing_prompt())
            
        # Check if we get different prompts (at least 10 unique ones)
        self.assertGreater(len(prompts), 10)

    def test_prompt_word_inclusion(self):
        """Test if generated prompts include words from word banks"""
        prompt = self.service.generate_drawing_prompt()
        
        # Check if at least one word from any word bank is in the prompt
        words_found = False
        for category in self.service.word_banks.values():
            if any(word in prompt.lower() for word in category):
                words_found = True
                break
                
        self.assertTrue(words_found)

    def test_prompt_template_usage(self):
        """Test if all prompt templates can be used"""
        template_usage = {template: False for template in self.service.prompt_templates}
        
        # Try multiple times to hit all templates
        for _ in range(100):
            prompt = self.service.generate_drawing_prompt()
            for template in self.service.prompt_templates:
                # Replace placeholders with .* for regex-like matching
                template_pattern = template
                for placeholder in ["{number}", "{adjective}", "{object}", "{location}"]:
                    if placeholder in template_pattern:
                        template_pattern = template_pattern.replace(placeholder, ".*")
                
                if prompt.startswith(template_pattern.split(".*")[0]):
                    template_usage[template] = True
                    
        # Check if all templates were used at least once
        self.assertTrue(all(template_usage.values()))

if __name__ == '__main__':
    unittest.main()
