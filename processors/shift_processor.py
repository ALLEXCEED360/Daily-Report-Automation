# processors/shift_processor.py
import os, re
from .base import Processor, ProcessorResult
from PIL import Image

class ShiftProcessor(Processor):
    NAME = "shifts"

    def _parse_number(self, text: str):
        if not text:
            return None
        m = re.search(r'(?:#?\s*Customers?[:\s\-]*)(\d{1,6})', text, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
        m2 = re.search(r'\b(\d{1,6})\b', text)
        if m2:
            try:
                return int(m2.group(1))
            except Exception:
                pass
        return None

    def _extract_with_gemini(self, image_path):
        prompt = """
Return only the number of customers found in this image, or the text 'NOT_FOUND' if none.
Look for '#Customers', 'Customers', 'No. of Customers', or similar.
"""
        resp = self.gemini.generate_from_image(prompt, image_path)
        if "error" in resp:
            return {"error": resp["error"]}
        text = resp.get("text","")
        num = self._parse_number(text)
        if num is not None:
            return {"num": num, "source": "gemini", "raw": text}
        # gemini didn't find numeric: return raw so fallback can try OCR
        return {"num": None, "source": "gemini", "raw": text}

    def _extract_with_ocr(self, image_path):
        try:
            import pytesseract
            txt = pytesseract.image_to_string(Image.open(image_path))
            num = self._parse_number(txt)
            return {"num": num, "source": "ocr", "raw": txt}
        except Exception as e:
            return {"error": f"pytesseract error: {e}"}

    def run(self, specific_day=None, dry_run: bool = False) -> ProcessorResult:
        others = self.config.get("others_dir")
        if not others:
            return ProcessorResult(self.NAME, False, {"error":"others_dir missing"})

        morning = os.path.join(others, "Morning_Shift.jpg")
        evening = os.path.join(others, "Evening_Shift.jpg")
        night = os.path.join(others, "Night_Shift.jpg")

        results = {"morning": None, "evening": None, "night": None, "details": {}}

        for label, path in (("morning", morning), ("evening", evening), ("night", night)):
            if not os.path.exists(path):
                results["details"][label] = {"error": "missing", "path": path}
                continue
            gem = self._extract_with_gemini(path)
            if gem.get("num") is not None:
                results[label] = gem["num"]
                results["details"][label] = gem
                continue
            # fallback to OCR
            ocr = self._extract_with_ocr(path)
            if ocr.get("num") is not None:
                results[label] = ocr["num"]
                results["details"][label] = ocr
            else:
                # no number found
                results["details"][label] = {"gemini": gem, "ocr": ocr}

        if dry_run:
            return ProcessorResult(self.NAME, True, {"parsed": results})

        if not self.excel.load_template(specific_day):
            return ProcessorResult(self.NAME, False, {"error":"could not load template"})

        if results["morning"] is not None:
            self.excel.sheet["E10"] = results["morning"]
        if results["evening"] is not None:
            self.excel.sheet["E12"] = results["evening"]
        if results["night"] is not None:
            self.excel.sheet["E14"] = results["night"]

        saved = self.excel.save_report(self.excel.template_path)
        return ProcessorResult(self.NAME, success=saved, details={"parsed": results})