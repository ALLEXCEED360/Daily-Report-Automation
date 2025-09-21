# handlers/gemini_handler.py
import os
import google.generativeai as genai
from PIL import Image
import json
import re
from typing import Dict

class GeminiVisionHandler:
    """
    Thin wrapper around google.generativeai to send (prompt + image) and return text.
    Does NOT store keys — expects caller to provide API key configuration externally.
    """
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Gemini API key required")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_from_image(self, prompt: str, image_path: str) -> Dict[str, str]:
        """Return {'text': ...} or {'error': ...}"""
        try:
            img = Image.open(image_path)
        except Exception as e:
            return {"error": f"Could not open image: {e}"}
        try:
            response = self.model.generate_content([prompt, img])
        except Exception as e:
            return {"error": f"Gemini API call failed: {e}"}
        text = getattr(response, "text", None) or str(response)
        return {"text": text}

    def extract_json_from_response_text(self, text: str):
        """Find a JSON block in returned text and parse it, or return None."""
        if not text:
            return None
        try:
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                return json.loads(m.group())
        except Exception:
            pass
        return None
