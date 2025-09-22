# processors/day3_report_processor.py
import os
import re
import json
from .base import Processor, ProcessorResult
from PIL import Image

class Day3ReportProcessor(Processor):
    NAME = "day3_report"

    def _prompt(self) -> str:
        return """
Please analyze this Day Report page image (FP/HOSE RUNNING RPT) and extract the PRODUCT TOTALS volumes for the following products:
- UNLEADED
- PLUS
- PREMIUM
- DIESEL

Return a JSON object with keys exactly:
{
  "unleaded": 1234.56,
  "plus": 234.56,
  "premium": 345.67,
  "diesel": 456.78
}
If a value isn't found, return null for that key.
"""

    def _to_float(self, s):
        if s is None:
            return None
        s = str(s).replace(",", "").replace("$", "").strip()
        s = s.rstrip("-")
        try:
            return float(s)
        except Exception:
            return None

    def _parse_numbers_near_labels(self, text):
        """
        Search the text for label variants and extract a nearby numeric volume.
        Returns dict with keys: unleaded, plus, premium, diesel
        """

        out = {"unleaded": None, "plus": None, "premium": None, "diesel": None}
        if not text:
            return out

        # normalize whitespace
        txt = " ".join(text.split())

        label_groups = {
            "unleaded": ["UNLEADED", "Unleaded", "REGULAR", "REG"],
            "plus": ["PLUS", "Plus", "PLUS (MID)"],
            "premium": ["PREMIUM", "Premium"],
            "diesel": ["DIESEL", "Diesel"]
        }

        # pattern: label ... number OR number ... label (within 60 chars)
        def find_near(labels):
            for label in labels:
                # label then number
                p1 = rf'{re.escape(label)}[^0-9\-\$]{{0,60}}([\d,]+(?:\.\d+)?)'
                m1 = re.search(p1, txt, re.IGNORECASE)
                if m1:
                    v = self._to_float(m1.group(1))
                    if v is not None:
                        return v
                # number then label
                p2 = rf'([\d,]+(?:\.\d+)?)[^0-9\-\$]{{0,60}}{re.escape(label)}'
                m2 = re.search(p2, txt, re.IGNORECASE)
                if m2:
                    v = self._to_float(m2.group(1))
                    if v is not None:
                        return v
            return None

        for key, labels in label_groups.items():
            out[key] = find_near(labels)

        return out

    def _extract_with_gemini(self, image_path):
        prompt = self._prompt()
        resp = self.gemini.generate_from_image(prompt, image_path)
        if "error" in resp:
            return {"error": resp["error"]}
        text = resp.get("text", "")
        # If Gemini returned JSON block, prefer that
        try:
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                data = json.loads(m.group())
                return {
                    "unleaded": self._to_float(data.get("unleaded") or data.get("Unleaded") or data.get("REG") or data.get("regular")),
                    "plus": self._to_float(data.get("plus") or data.get("Plus")),
                    "premium": self._to_float(data.get("premium") or data.get("Premium")),
                    "diesel": self._to_float(data.get("diesel") or data.get("Diesel")),
                    "raw_text": text
                }
        except Exception:
            pass

        # Otherwise parse heuristically from returned text
        parsed = self._parse_numbers_near_labels(text)
        parsed["raw_text"] = text
        return parsed

    def _extract_with_ocr(self, image_path):
        try:
            import pytesseract
            txt = pytesseract.image_to_string(Image.open(image_path))
            parsed = self._parse_numbers_near_labels(txt)
            parsed["raw_text"] = txt
            return parsed
        except Exception as e:
            return {"error": f"pytesseract error: {e}"}

    def run(self, specific_day=None, dry_run: bool = False) -> ProcessorResult:
        image_path = self.config.get("image_path")
        if not image_path or not os.path.exists(image_path):
            return ProcessorResult(self.NAME, False, {"error": "image missing", "image_path": image_path})

        # Try Gemini first
        parsed = self._extract_with_gemini(image_path)
        details = {"gemini": parsed if isinstance(parsed, dict) else {"raw": parsed}}

        # If gemini returned no useful numbers, fallback to OCR
        if isinstance(parsed, dict) and all(parsed.get(k) is None for k in ("unleaded","plus","premium","diesel")):
            ocr_parsed = self._extract_with_ocr(image_path)
            details["ocr"] = ocr_parsed
            # prefer OCR values if they exist
            for k in ("unleaded","plus","premium","diesel"):
                if parsed.get(k) is None and isinstance(ocr_parsed, dict):
                    parsed[k] = ocr_parsed.get(k)

        if dry_run:
            return ProcessorResult(self.NAME, True, {"parsed": parsed, "details": details})

        # Write to Excel
        if not self.excel.load_template(specific_day):
            return ProcessorResult(self.NAME, False, {"error": "could not load template", "details": details})

        # Map:
        # UNLEADED -> F26
        # PLUS     -> H26
        # PREMIUM  -> G26
        # DIESEL   -> E26
        if parsed.get("unleaded") is not None:
            self.excel.sheet["F26"] = parsed.get("unleaded")
        if parsed.get("plus") is not None:
            self.excel.sheet["H26"] = parsed.get("plus")
        if parsed.get("premium") is not None:
            self.excel.sheet["G26"] = parsed.get("premium")
        if parsed.get("diesel") is not None:
            self.excel.sheet["E26"] = parsed.get("diesel")

        saved = self.excel.save_report(self.excel.template_path)
        return ProcessorResult(self.NAME, success=saved, details={"parsed": parsed, "details": details})
