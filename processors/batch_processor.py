# processors/batch_processor.py
import os
import re
from .base import Processor, ProcessorResult

class BatchProcessor(Processor):
    NAME = "batch"

    def _prompt(self) -> str:
        return """
Please analyze this Batch Report image and return the dollar amount that corresponds to the EBT total.
Look for lines containing the word 'EBT' (or 'E B T') and a dollar amount or the word 'Total' near EBT.
Return a short line such as: EBT: 123.45
If you cannot find an EBT amount, return NOT_FOUND.
"""

    def _parse_currency_like(self, text: str):
        """
        Find a numeric currency in the text near an 'EBT' mention.
        Returns float or None.
        """
        if not text:
            return None

        # Normalize spacing
        txt = text.replace("\n", " ").replace("\r", " ")

        # 1) Look for patterns like "EBT ... 1,234.56" or "EBT: $123.45" or "EBT TOTAL 123.45"
        m = re.search(r'EBT[^0-9\.\-]*([\$\-]?\s*\d{1,3}(?:[,]\d{3})*(?:\.\d{1,2})?)', txt, re.IGNORECASE)
        if m:
            numstr = m.group(1)
            return self._to_float(numstr)

        # 2) Look for "EBT" and a number after it within 30 chars
        m2 = re.search(r'EBT(.{0,60}?)([\$\-]?\s*\d{1,3}(?:[,]\d{3})*(?:\.\d{1,2})?)', txt, re.IGNORECASE)
        if m2:
            return self._to_float(m2.group(2))

        # 3) If a "TOTAL" appears near "EBT", capture a number near "TOTAL"
        m3 = re.search(r'(?:EBT.*?TOTAL|TOTAL.*?EBT)(.{0,60}?)([\$\-]?\s*\d{1,3}(?:[,]\d{3})*(?:\.\d{1,2})?)', txt, re.IGNORECASE)
        if m3:
            return self._to_float(m3.group(2))

        # 4) As a last resort, capture the first currency-like number in text
        m4 = re.search(r'([\$\-]?\s*\d{1,3}(?:[,]\d{3})*(?:\.\d{1,2})?)', txt)
        if m4:
            return self._to_float(m4.group(1))

        return None

    def _to_float(self, s):
        """Normalize strings like '$1,234.56', '1,234.56', '122.00-' to float."""
        if not s:
            return None
        s = s.replace("$", "").replace(" ", "").replace("\u200b","")
        # handle trailing dash like '122.00-'
        s = s.rstrip("-")
        s = s.replace(",", "")
        try:
            return float(s)
        except Exception:
            return None

    def _extract_with_gemini(self, image_path: str):
        prompt = self._prompt()
        resp = self.gemini.generate_from_image(prompt, image_path)
        if "error" in resp:
            return {"error": resp["error"]}
        text = resp.get("text", "")
        # Attempt to parse a currency near "EBT"
        val = self._parse_currency_like(text)
        return {"value": val, "raw": text}

    def _extract_with_ocr(self, image_path: str):
        # fallback using pytesseract OCR if Gemini didn't return usable value
        try:
            import pytesseract
            from PIL import Image
            txt = pytesseract.image_to_string(Image.open(image_path))
            val = self._parse_currency_like(txt)
            return {"value": val, "raw": txt}
        except Exception as e:
            return {"error": f"pytesseract error: {e}"}

    def run(self, specific_day=None, dry_run: bool = False) -> ProcessorResult:
        """
        Expects config key 'image_path' to point to batch_report.jpg in Others/.
        Reads EBT value and adds it to cell Z10 (summing with existing numeric value).
        """
        image_path = self.config.get("image_path")
        if not image_path or not os.path.exists(image_path):
            return ProcessorResult(self.NAME, False, {"error": "image missing", "image_path": image_path})

        # Try Gemini
        gem = self._extract_with_gemini(image_path)
        extracted_val = gem.get("value")
        details = {"gemini": gem}

        # Fallback to OCR if Gemini didn't find a value
        if extracted_val is None:
            ocr = self._extract_with_ocr(image_path)
            details["ocr"] = ocr
            extracted_val = ocr.get("value") if isinstance(ocr, dict) else None

        if extracted_val is None:
            return ProcessorResult(self.NAME, False, {"error": "EBT not found", "details": details})

        if dry_run:
            return ProcessorResult(self.NAME, True, {"extracted_ebt": extracted_val, "details": details})

        # Load excel template
        if not self.excel.load_template(specific_day):
            return ProcessorResult(self.NAME, False, {"error": "could not load template"})

        # Read existing value in Z10 (tolerant)
        try:
            cur = self.excel.sheet.get('Z10').value
        except Exception:
            cur = None

        def _to_num(x):
            try:
                if x is None:
                    return 0.0
                if isinstance(x, (int, float)):
                    return float(x)
                # string: remove non-numeric
                s = str(x).replace("$", "").replace(",", "").strip()
                return float(s) if s != "" else 0.0
            except Exception:
                return 0.0

        cur_num = _to_num(cur)
        new_total = cur_num + float(extracted_val)

        # Write back to Z10
        self.excel.sheet['Z10'] = new_total
        saved = self.excel.save_report(self.excel.template_path)

        details.update({"extracted_ebt": extracted_val, "previous_Z10": cur_num, "new_Z10": new_total})
        return ProcessorResult(self.NAME, success=saved, details=details)
