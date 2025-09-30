# handlers/gemini_handler.py
import time
import json
import re
from typing import Dict
from PIL import Image
import google.generativeai as genai

class GeminiVisionHandler:
    """
    Wrapper that auto-detects available models and uses them.
    """

    def __init__(self, api_key: str, preferred_model: str = "gemini-1.5-flash", max_retries: int = 3):
        if not api_key:
            raise ValueError("Gemini API key required")
        
        genai.configure(api_key=api_key)
        self.max_retries = max_retries
        
        # Try to find an available model
        print("Detecting available Gemini models...")
        available_models = self._get_available_models()
        
        if not available_models:
            raise RuntimeError("No available models found for this API key")
        
        # Try preferred model first, then fallback to any available
        if preferred_model in available_models:
            self.preferred_model_name = preferred_model
        else:
            # Use first available model
            self.preferred_model_name = available_models[0]
            print(f"Preferred model '{preferred_model}' not available.")
        
        print(f"Using model: {self.preferred_model_name}")
        print(f"Available models: {', '.join(available_models[:5])}")
        
        self._model = genai.GenerativeModel(self.preferred_model_name)

    def _get_available_models(self):
        """Get list of available model names that support generateContent."""
        try:
            models = genai.list_models()
            available = []
            for m in models:
                # Check if model supports generateContent
                if hasattr(m, 'supported_generation_methods'):
                    methods = m.supported_generation_methods
                    if 'generateContent' in methods:
                        # Extract just the model name (remove 'models/' prefix if present)
                        name = m.name
                        if name.startswith('models/'):
                            name = name[7:]
                        available.append(name)
            return available
        except Exception as e:
            print(f"Error listing models: {e}")
            return []

    def generate_from_image(self, prompt: str, image_path: str) -> Dict[str, str]:
        """
        Generate text from image using the configured model.
        Returns {"text": "..."} on success or {"error": "..."} on failure.
        """
        # Open image
        try:
            image = Image.open(image_path)
        except Exception as e:
            return {"error": f"Could not open image '{image_path}': {e}"}

        # Try calling model with retries
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self._model.generate_content([prompt, image])
                text = getattr(resp, "text", None) or str(resp)
                return {"text": text}
            
            except Exception as e:
                err_text = str(e).lower()
                
                # Check if it's a rate limit error
                if "quota" in err_text or "rate" in err_text or "429" in err_text or "exceeded" in err_text:
                    if attempt < self.max_retries:
                        backoff = (2 ** attempt) * 2
                        print(f"Rate limit hit (attempt {attempt}/{self.max_retries}), waiting {backoff}s...")
                        time.sleep(backoff)
                        continue
                    else:
                        return {"error": f"Max retries exceeded. Rate limit error: {str(e)}"}
                else:
                    # Non-rate-limit error, return immediately
                    return {"error": str(e)}
        
        return {"error": "Max retries exceeded"}

    def extract_json_from_response_text(self, text: str):
        """Parse the first JSON object found in text."""
        if not text:
            return None
        try:
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                return json.loads(m.group())
        except Exception:
            pass
        return None