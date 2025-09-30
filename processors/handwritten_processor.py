# processors/handwritten_processor.py
import os
import re
import json
from .base import Processor, ProcessorResult
from PIL import Image

class HandwrittenProcessor(Processor):
    NAME = "handwritten"

    def _prompt(self) -> str:
        return """
You will be given an image of a handwritten daily report. Extract the following values:

- Morning customers/count (labelled 'Morning' or 'Morning Shift' or similar) - can be decimal
- Evening customers/count (labelled 'Evening' or 'Evening Shift') - can be decimal
- Night customers/count (labelled 'Night' or 'Night Shift') - can be decimal
- Total Cash (labelled 'Total Cash', 'Total Cash:' or similar)
- Any numeric values listed under a section/label 'Additional' (could be multiple lines under that heading) — return the sum of those numbers.
- Game in and Game out values (labels like 'Game in', 'Game out', 'Game In', 'Game-Out', etc.)

Return a JSON object exactly like:
{
  "morning": 358.75,    # float or null
  "evening": 456.50,    # float or null
  "night": 78.25,       # float or null
  "total_cash": 1234.56,# float or null
  "additional_sum": 45.67, # float or null
  "game_in": 12.34,     # float or null
  "game_out": 56.78     # float or null
}

If a value cannot be found, set it to null.
"""

    def _to_float(self, s):
        """Return a float for currency-like strings."""
        if s is None:
            return None
        s = str(s)
        # remove common junk
        s = s.replace("$", "").replace(",", "").replace("\u200b", "").strip()
        s = s.rstrip("-")
        # parentheses => negative
        if s.startswith("(") and s.endswith(")"):
            s = "-" + s[1:-1]
        s = s.lstrip("+").strip()
        try:
            return float(s)
        except Exception:
            m = re.search(r'(-?\d+(?:\.\d+)?)', s)
            if m:
                try:
                    return float(m.group(1))
                except:
                    return None
            return None

    def _parse_first_number(self, text):
        """Parse first number (can be decimal) from text."""
        if not text:
            return None
        # Look for number with optional decimal
        m = re.search(r'(?:#?\s*Customers?[:\s\-]*)([\d,]+(?:\.\d+)?)', text, re.IGNORECASE)
        if m:
            return self._to_float(m.group(1))
        m2 = re.search(r'\b([\d,]+(?:\.\d+)?)\b', text)
        if m2:
            return self._to_float(m2.group(1))
        return None

    def _find_label_near_number(self, text, labels, window=60, allow_decimal=True):
        """
        Search for label variants and return number near them.
        Returns float or None.
        """
        if not text:
            return None
        txt = " ".join(text.split())
        # pattern decimal precision variable
        decimal_part = r'(?:\.\d{1,4})?' if allow_decimal else r''
        for lbl in labels:
            # label then number (allow decimals)
            p1 = rf'{re.escape(lbl)}[^0-9\-\$\.\,]{{0,{window}}}([\$\-\(\)]?\s*\d{{1,7}}(?:[,]\d{{3}})*{decimal_part}\)?)'
            m1 = re.search(p1, txt, re.IGNORECASE)
            if m1:
                val = self._to_float(m1.group(1))
                if val is not None:
                    return val
            # number then label
            p2 = rf'([\$\-\(\)]?\s*\d{{1,7}}(?:[,]\d{{3}})*{decimal_part}\)?)[^0-9\-\$\.\,]{{0,{window}}}{re.escape(lbl)}'
            m2 = re.search(p2, txt, re.IGNORECASE)
            if m2:
                val = self._to_float(m2.group(1))
                if val is not None:
                    return val
        return None

    def _sum_additional_section(self, text):
        """
        Find 'Additional' label, capture following lines / nearby area and sum numeric values found there.
        """
        if not text:
            return None
        lower = text.lower()
        idx = lower.find("additional")
        if idx == -1:
            for alt in ("add'l", "adds", "additional expenses", "additional charges"):
                idx = lower.find(alt)
                if idx != -1:
                    break
        if idx == -1:
            return None

        region = text[max(0, idx-80): idx + 400]
        nums = re.findall(r'[-\$\(]?\s*\d{1,3}(?:[,]\d{3})*(?:\.\d{1,4})?\)?', region)
        vals = []
        for n in nums:
            v = self._to_float(n)
            if v is not None:
                vals.append(v)
        if not vals:
            return None
        return sum(vals)

    def _extract_with_gemini(self, image_path):
        prompt = self._prompt()
        resp = self.gemini.generate_from_image(prompt, image_path)
        if "error" in resp:
            return {"error": resp["error"]}
        text = resp.get("text", "")

        # Try to parse JSON block
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group())
                parsed_conv = {
                    "morning": self._to_float(parsed.get("morning")),
                    "evening": self._to_float(parsed.get("evening")),
                    "night": self._to_float(parsed.get("night")),
                    "total_cash": self._to_float(parsed.get("total_cash")),
                    "additional_sum": self._to_float(parsed.get("additional_sum")),
                    "game_in": self._to_float(parsed.get("game_in")),
                    "game_out": self._to_float(parsed.get("game_out"))
                }
                return parsed_conv
            except Exception:
                pass

        # Heuristic parsing from returned text - NOW ALLOWS DECIMALS
        morning = self._find_label_near_number(text, ["Morning", "Morning Shift", "Morn"], allow_decimal=True)
        evening = self._find_label_near_number(text, ["Evening", "Evening Shift", "Eve"], allow_decimal=True)
        night = self._find_label_near_number(text, ["Night", "Night Shift"], allow_decimal=True)

        if morning is None:
            morning = self._parse_first_number(text)
        if evening is None:
            nums = re.findall(r'\b([\d,]+(?:\.\d+)?)\b', text)
            if nums and len(nums) >= 2:
                evening = self._to_float(nums[1])
        if night is None:
            nums = re.findall(r'\b([\d,]+(?:\.\d+)?)\b', text)
            if nums and len(nums) >= 3:
                night = self._to_float(nums[2])

        total_cash = self._find_label_near_number(text, ["Total Cash", "Total Cash:", "Total Cash -", "Total", "Cash Total"], allow_decimal=True)
        if total_cash is None:
            all_nums = re.findall(r'[-\$\(]?\s*\d{1,3}(?:[,]\d{3})*(?:\.\d{1,4})?\)?', text)
            parsed_vals = [self._to_float(n) for n in all_nums if self._to_float(n) is not None]
            if parsed_vals:
                total_cash = max(parsed_vals)

        additional_sum = self._sum_additional_section(text)

        # extract game in / game out (allow decimals)
        game_in = self._find_label_near_number(text, ["Game in", "Game In", "Game-In", "Gamein", "Game in:"], allow_decimal=True)
        game_out = self._find_label_near_number(text, ["Game out", "Game Out", "Game-Out", "Gameout", "Game out:"], allow_decimal=True)

        return {
            "morning": morning,
            "evening": evening,
            "night": night,
            "total_cash": total_cash,
            "additional_sum": additional_sum,
            "game_in": game_in,
            "game_out": game_out,
            "raw_text": text
        }

    def _extract_with_ocr(self, image_path):
        try:
            import pytesseract
            txt = pytesseract.image_to_string(Image.open(image_path))
            morning = self._find_label_near_number(txt, ["Morning", "Morning Shift", "Morn"], allow_decimal=True)
            evening = self._find_label_near_number(txt, ["Evening", "Evening Shift", "Eve"], allow_decimal=True)
            night = self._find_label_near_number(txt, ["Night", "Night Shift"], allow_decimal=True)
            
            if morning is None:
                morning = self._parse_first_number(txt)
            if evening is None:
                nums = re.findall(r'\b([\d,]+(?:\.\d+)?)\b', txt)
                if nums and len(nums) >= 2:
                    evening = self._to_float(nums[1])
            if night is None:
                nums = re.findall(r'\b([\d,]+(?:\.\d+)?)\b', txt)
                if nums and len(nums) >= 3:
                    night = self._to_float(nums[2])

            total_cash = self._find_label_near_number(txt, ["Total Cash", "Total Cash:", "Total Cash -", "Total", "Cash Total"], allow_decimal=True)
            if total_cash is None:
                all_nums = re.findall(r'[-\$\(]?\s*\d{1,3}(?:[,]\d{3})*(?:\.\d{1,4})?\)?', txt)
                parsed_vals = [self._to_float(n) for n in all_nums if self._to_float(n) is not None]
                if parsed_vals:
                    total_cash = max(parsed_vals)

            additional_sum = self._sum_additional_section(txt)

            # game in / game out from OCR
            game_in = self._find_label_near_number(txt, ["Game in", "Game In", "Game-In", "Gamein", "Game in:"], allow_decimal=True)
            game_out = self._find_label_near_number(txt, ["Game out", "Game Out", "Game-Out", "Gameout", "Game out:"], allow_decimal=True)

            return {
                "morning": morning,
                "evening": evening,
                "night": night,
                "total_cash": total_cash,
                "additional_sum": additional_sum,
                "game_in": game_in,
                "game_out": game_out,
                "raw_text": txt
            }
        except Exception as e:
            return {"error": f"pytesseract error: {e}"}

    def run(self, specific_day=None, dry_run: bool = False) -> ProcessorResult:
        image_path = self.config.get("image_path")
        if not image_path or not os.path.exists(image_path):
            return ProcessorResult(self.NAME, False, {"error": "image missing", "image_path": image_path})

        # Try Gemini first
        parsed = self._extract_with_gemini(image_path)
        details = {"gemini": parsed if isinstance(parsed, dict) else {"raw": parsed}}

        # Determine whether OCR fallback is needed
        needs_ocr = False
        if not isinstance(parsed, dict):
            needs_ocr = True
        else:
            useful = any(parsed.get(k) is not None for k in ("morning", "evening", "night", "total_cash", "additional_sum", "game_in", "game_out"))
            if not useful:
                needs_ocr = True

        if needs_ocr:
            ocr = self._extract_with_ocr(image_path)
            details["ocr"] = ocr
            if isinstance(ocr, dict):
                # prefer OCR values where parsed missing
                for k in ("morning", "evening", "night", "total_cash", "additional_sum", "game_in", "game_out"):
                    if parsed.get(k) is None:
                        parsed[k] = ocr.get(k)

        if dry_run:
            return ProcessorResult(self.NAME, True, {"parsed": parsed, "details": details})

        # write to excel
        if not self.excel.load_template(specific_day):
            return ProcessorResult(self.NAME, False, {"error": "could not open template"})

        if parsed.get("morning") is not None:
            self.excel.sheet["D9"] = parsed.get("morning")
        if parsed.get("evening") is not None:
            self.excel.sheet["D11"] = parsed.get("evening")
        if parsed.get("night") is not None:
            self.excel.sheet["D13"] = parsed.get("night")
        if parsed.get("total_cash") is not None:
            self.excel.sheet["L14"] = parsed.get("total_cash")
        if parsed.get("additional_sum") is not None:
            self.excel.sheet["Z17"] = parsed.get("additional_sum")
        # writes for games
        if parsed.get("game_in") is not None:
            self.excel.sheet["F34"] = parsed.get("game_in")
        if parsed.get("game_out") is not None:
            self.excel.sheet["F35"] = parsed.get("game_out")

        saved = self.excel.save_report(self.excel.template_path)
        return ProcessorResult(self.NAME, success=saved, details={"parsed": parsed, "details": details})