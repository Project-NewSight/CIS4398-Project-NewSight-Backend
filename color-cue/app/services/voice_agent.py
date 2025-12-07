
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

class VoiceCommandAgent:
    """
    Voice Command agent that uses LLM to intelligently route user requests
    """
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        
        self.api_key = api_key
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"  # Fixed: was self.api_key

        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(current_dir, 'system_prompt.txt')

        try: 
            with open(prompt_path, 'r', encoding="utf-8") as f:
                self.system_prompt = f.read()
        except FileNotFoundError:
            raise FileNotFoundError("system_prompt.txt file not found")
    
    def route_command(self, user_command: str):
        """
        Send user command to GroqCloud model and get structured response
        Expected model output: JSON string with keys 'feature', 'confidence', 'extracted_params'
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_command}
            ],
            "max_completion_tokens":1024,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()
            response_text = data["choices"][0]["message"]["content"].strip()

            result = json.loads(response_text)

            if not self._validate_response(result):
                return self._create_error_response("Invalid response format")
            
            return result
        
        except json.JSONDecodeError as e:
            return self._create_error_response(f"Failed to parse response: {str(e)}")
        
        except Exception as e:
            return self._create_error_response(f"An error occurred in agent: {str(e)}")
        
    def _validate_response(self, result: dict) -> bool:
        """
        Validate response structure
        """
        required_keys = {'feature', 'confidence', 'extracted_params'}
        return all(key in result for key in required_keys)
    
    def _create_error_response(self, error_message: str):
        """
        Create standardized error response
        """
        return {
            'feature': None,
            'confidence': 0.0,
            'extracted_params': {
                'query': '',
                'error': error_message
            }
        }