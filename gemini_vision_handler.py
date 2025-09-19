# gemini_handler.py
import os
import google.generativeai as genai
from PIL import Image
import json
import re

class GeminiVisionHandler:
    """
    A simple wrapper around Google Gemini Vision to extract lotto values from images.
    Reads the Gemini API key from the caller (in tests we read from the environment).
    """

    def __init__(self, api_key: str):
        """Initialize Gemini Vision handler. Pass a valid API key (preferably from env)."""
        if not api_key:
            raise ValueError("Gemini API key is required")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def _extract_json_from_text(self, text: str):
        """Attempt to find a JSON object inside the model response text and parse it."""
        if not text:
            return None
        try:
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
        except json.JSONDecodeError:
            return None
        return None

    def extract_lotto_data(self, image_path: str):
        """
        Extract specific lotto data using Gemini Vision.
        Returns a dict with keys:
          - drw_gm_net_sales
          - drw_gm_cashes
          - scratch_cashes
          - total_cashes
        On failure, returns a dict with "error" and "raw_response" (if available).
        """
        try:
            image = Image.open(image_path)
        except Exception as e:
            return {"error": f"Could not open image: {e}"}

        prompt = """
Please analyze this Lotto Machine Report image and extract the following specific values:

1. Look for "DRW GM NET SALES" (or "DRAW GM NET SALES") and get the dollar amount after it
2. Look for "DRW GM CASHES" (or "DRAW GM CASHES") and get the dollar amount after it
3. Look for "SCRATCH CASHES" and get the dollar amount after it

IMPORTANT:
- Include decimal points in your response (e.g., if you see $38.50, return 38.50 not 3850)
- Remove dollar signs and any negative signs, but keep decimal points
- If a value shows as $122.00-, just return 122.00

Please respond in this exact JSON format if possible:
{
  "drw_gm_net_sales": <number_with_decimals_or_null>,
  "drw_gm_cashes": <number_with_decimals_or_null>,
  "scratch_cashes": <number_with_decimals_or_null>,
  "total_cashes": <sum_or_null>
}
If JSON is not possible, provide clearly labelled lines like:
DRW GM NET SALES: $38.50
DRW GM CASHES: $20.00
SCRATCH CASHES: $18.50
"""

        try:
            # Call the model with the image and prompt.
            response = self.model.generate_content([prompt, image])
        except Exception as e:
            return {"error": f"Gemini API call failed: {e}"}

        # Some SDK responses put text on .text, others may return other shapes; handle both
        result_text = None
        try:
            if hasattr(response, "text") and response.text:
                result_text = response.text
            else:
                # fallback to string conversion
                result_text = str(response)
        except Exception:
            result_text = str(response)

        # Try to parse JSON from the response text
        parsed = self._extract_json_from_text(result_text)
        if parsed:
            # Normalize and ensure numeric sums if applicable
            try:
                # compute total_cashes if missing and if parts present
                if parsed.get("drw_gm_cashes") is not None and parsed.get("scratch_cashes") is not None:
                    if parsed.get("total_cashes") in (None, "", 0):
                        # attempt numeric addition, but be defensive
                        try:
                            parsed["total_cashes"] = float(parsed["drw_gm_cashes"]) + float(parsed["scratch_cashes"])
                        except Exception:
                            # leave as-is if unable to convert
                            parsed["total_cashes"] = parsed.get("total_cashes")
                return parsed
            except Exception:
                # if anything unexpected, still return parsed plus raw response
                parsed["_note"] = "parsed JSON but normalization failed"
                parsed["raw_response"] = result_text
                return parsed

        # If no JSON, return helpful error + raw response to help debugging
        return {"error": "Could not find JSON in response", "raw_response": result_text}

    def extract_all_text(self, image_path: str):
        """
        Ask Gemini to extract all text from the image (useful for debugging / template tuning).
        Returns the raw textual response or an error dict.
        """
        try:
            image = Image.open(image_path)
        except Exception as e:
            return {"error": f"Could not open image: {e}"}

        prompt = "Please extract all text you can see in this image. List everything clearly."

        try:
            response = self.model.generate_content([prompt, image])
        except Exception as e:
            return {"error": f"Gemini API call failed: {e}"}

        try:
            if hasattr(response, "text") and response.text:
                return response.text
            else:
                return str(response)
        except Exception:
            return {"error": "Unexpected response format", "raw_response": str(response)}


# --------------------
# Test harness (safe: no hardcoded key)
# --------------------
def test_gemini_vision():
    # Read API key from environment (do NOT hardcode keys in repo)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment. Set it and re-run the test.")

    handler = GeminiVisionHandler(api_key)

    # Example usage: extract lotto values from sample_report.jpg
    print("🎯 Extracting specific lotto values...")
    result = handler.extract_lotto_data("sample_report.jpg")

    if result and not result.get("error"):
        print("\n✅ Extraction Results:")
        print(f"DRW GM NET SALES: {result.get('drw_gm_net_sales')}")
        print(f"DRW GM CASHES: {result.get('drw_gm_cashes')}")
        print(f"SCRATCH CASHES: {result.get('scratch_cashes')}")
        print(f"TOTAL CASHES: {result.get('total_cashes')}")
    else:
        print("\n❌ Failed to extract data:")
        print(result)


if __name__ == "__main__":
    test_gemini_vision()
