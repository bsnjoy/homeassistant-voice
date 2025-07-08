#!/usr/bin/env python3
import unittest
import sys
import os
import config

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ai import send_to_openai

class TestAIIntegration(unittest.TestCase):
    """Integration test for the AI module that makes an actual API call."""

    def test_send_to_openai_real_call(self):
        """Test send_to_openai with a real API call to OpenAI."""
        # Make an actual call to OpenAI
        result = send_to_openai("Привет как тебя зовут?")
        
        # Verify we got a non-empty response
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
        print(f"OpenAI response: {result}")

if __name__ == '__main__':
    unittest.main()
