# processors/handwritten_lotto_end_processor.py
import os
import re
import json
from .base import Processor, ProcessorResult
from PIL import Image

class HandwrittenLottoEndProcessor(Processor):
    NAME = "handwritten_lotto_end"

    def _to_number(self, s):
        """Normalize a numeric token to float (or int-like float)."""
        if s is None:
            return None
        s = str(s)
        s = s.replace("$", "").replace(",", "").replace("\u200b", "").strip()
        s = s.rstrip("-")
        if s.startswith("(") and s.endswith(")"):
            s = "-" + s[1:-1]
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

    def _extract_numbers_after_header_lines(self, lines, header_idx, max_needed=20):
        nums = []
        lookahead = 80
        for i in range(header_idx + 1, min(len(lines), header_idx + 1 + lookahead)):
            if len(nums) >= max_needed:
                break
            line = lines[i].strip()
            if not line:
                continue
            m = re.search(r'(-?\d{1,6}(?:\.\d{1,4})?)', line)
            if m:
                val = self._to_number(m.group(1))
                if val is not None:
                    nums.append(val)
                    continue
            m2 = re.search(r'([\$\-\(]?\s*\d{1,3}(?:[,]\d{3})*(?:\.\d{1,4})?\)?)', line)
            if m2:
                val = self._to_number(m2.group(1))
                if val is not None:
                    nums.append(val)
                    continue
            tokens = re.findall(r'[-]?\d+(?:\.\d+)?', line)
            if tokens:
                val = self._to_number(tokens[-1])
                if val is not None:
                    nums.append(val)
        return nums

    def _find_header_index(self, lines):
        header_patterns = [r'End\s*no', r'End\s*No', r'End\s*n[oO]\b', r'End\s*#', r'End\s*No\.', r'\bEnd\b']
        section_markers = ['daily lotto', 'daily lotto section', 'daily lotto report', 'daily lotto totals', 'daily lotto:']
        for idx, line in enumerate(lines):
            for pat in header_patterns:
                if re.search(pat, line, re.IGNORECASE):
                    return idx
        for idx, line in enumerate(lines):
            for marker in section_markers:
                if marker in line.lower():
                    for j in range(idx, min(len(lines), idx + 20)):
                        l = lines[j]
                        if re.search(r'\bEnd\b', l, re.IGNORECASE) or re.search(r'End\s*no', l, re.IGNORECASE):
                            return j
                    return idx
        for idx, line in enumerate(lines):
            if 'end' in line.lower():
                return idx
        return -1

    def _extract_from_text(self, text, max_needed=20):
        if not text:
            return {"values": [], "raw_text": ""}
        raw_lines = text.splitlines()
        lines = [ln.strip() for ln in raw_lines if ln is not None]
        header_idx = self._find_header_index(lines)
        values = []
        raw_snippet = "\n".join(lines[max(0, header_idx - 4): header_idx + 40]) if header_idx >= 0 else "\n".join(lines[:80])
        if header_idx >= 0:
            values = self._extract_numbers_after_header_lines(lines, header_idx, max_needed=max_needed)
        if len(values) < max_needed:
            msec = re.search(r'(Daily\s+Lotto|Daily\s+Lotto:|Daily\s+Lotto\s+Section|Daily Lotto)', text, re.IGNORECASE)
            start_pos = msec.end() if msec else 0
            tail = text[start_pos:]
            all_nums = re.findall(r'(-?\d{1,6}(?:\.\d{1,4})?)', tail)
            extracted = []
            for n in all_nums:
                v = self._to_number(n)
                if v is not None:
                    extracted.append(v)
                if len(extracted) >= max_needed:
                    break
            if extracted:
                for v in extracted:
                    if len(values) >= max_needed:
                        break
                    values.append(v)
        if len(values) > max_needed:
            values = values[:max_needed]
        while len(values) < max_needed:
            values.append(None)
        return {"values": values, "raw_text": raw_snippet}

    def _extract_with_gemini(self, image_path, max_needed=20):
        prompt = (
            "Read this Handwritten Report image. Locate the 'Daily Lotto' section and the 'End no' "
            "column (or similar). Return the End no values top-to-bottom as a JSON array. "
            "If not found, return NOT_FOUND. Respond with JSON like: {\"end_values\": [123,124,...] }"
        )
        resp = self.gemini.generate_from_image(prompt, image_path)
        if "error" in resp:
            return {"error": resp["error"]}
        text = resp.get("text", "")
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                j = json.loads(m.group())
                arr = j.get("end_values") or j.get("end_no") or j.get("end") or j.get("values")
                if isinstance(arr, list):
                    norm = [self._to_number(x) for x in arr][:max_needed]
                    while len(norm) < max_needed:
                        norm.append(None)
                    return {"values": norm, "raw_text": text}
            except Exception:
                pass
        return self._extract_from_text(text, max_needed=max_needed)

    def _extract_with_ocr(self, image_path, max_needed=20):
        try:
            import pytesseract
            txt = pytesseract.image_to_string(Image.open(image_path))
            return self._extract_from_text(txt, max_needed=max_needed)
        except Exception as e:
            return {"error": f"pytesseract error: {e}", "values": [], "raw_text": ""}

    def run(self, specific_day=None, dry_run: bool = False) -> ProcessorResult:
        configured_image = self.config.get("image_path")
        others_dir = self.config.get("others_dir")
        
        if not others_dir:
            if configured_image:
                others_dir = os.path.dirname(os.path.abspath(configured_image))
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                others_dir = os.path.join(base_dir, "..", "Others")
        
        # Process Handwritten_Report.jpg (always required) - maps to I26:AB26
        if not configured_image or not os.path.exists(configured_image):
            return ProcessorResult(self.NAME, False, {"error": "Handwritten_Report.jpg missing", "image_path": configured_image})
        
        # Extract from Report1 (20 values for I26:AB26)
        gem1 = self._extract_with_gemini(configured_image, max_needed=20)
        details = {"report1": gem1}
        values1 = gem1.get("values") if isinstance(gem1, dict) else None
        
        if (not values1) or all(v is None for v in values1):
            ocr1 = self._extract_with_ocr(configured_image, max_needed=20)
            details["report1_ocr"] = ocr1
            values1 = ocr1.get("values") if isinstance(ocr1, dict) else values1
        
        if values1 is None:
            values1 = [None] * 20
        
        # Check for Handwritten_Report2.jpg (optional) - maps to I33:X33
        alt_file = os.path.join(others_dir, "Handwritten_Report2.jpg")
        values2 = None
        
        if os.path.exists(alt_file):
            gem2 = self._extract_with_gemini(alt_file, max_needed=16)
            details["report2"] = gem2
            values2 = gem2.get("values") if isinstance(gem2, dict) else None
            
            if (not values2) or all(v is None for v in values2):
                ocr2 = self._extract_with_ocr(alt_file, max_needed=16)
                details["report2_ocr"] = ocr2
                values2 = ocr2.get("values") if isinstance(ocr2, dict) else values2
            
            if values2 is None:
                values2 = [None] * 16
        
        if dry_run:
            return ProcessorResult(self.NAME, True, {
                "report1_file": configured_image,
                "report1_values": values1,
                "report2_file": alt_file if values2 else None,
                "report2_values": values2,
                "details": details
            })
        
        # Write to Excel
        if not self.excel.load_template(specific_day):
            return ProcessorResult(self.NAME, False, {"error": "could not open template", "details": details})
        
        # Write Report1 values to I26:AB26
        col_letters_26 = ["I","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","X","Y","Z","AA","AB"]
        for idx, col in enumerate(col_letters_26):
            val = values1[idx] if idx < len(values1) else None
            if val is None:
                continue
            try:
                if abs(val - int(val)) < 1e-9:
                    self.excel.sheet[f"{col}26"] = int(val)
                else:
                    self.excel.sheet[f"{col}26"] = float(val)
            except Exception:
                self.excel.sheet[f"{col}26"] = val
        
        # Write Report2 values to I33:X33 (only if Report2 exists)
        if values2:
            col_letters_33 = ["I","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","X"]
            for idx, col in enumerate(col_letters_33):
                val = values2[idx] if idx < len(values2) else None
                if val is None:
                    continue
                try:
                    if abs(val - int(val)) < 1e-9:
                        self.excel.sheet[f"{col}33"] = int(val)
                    else:
                        self.excel.sheet[f"{col}33"] = float(val)
                except Exception:
                    self.excel.sheet[f"{col}33"] = val
        
        saved = self.excel.save_report(self.excel.template_path)
        return ProcessorResult(self.NAME, success=saved, details={
            "report1_file": configured_image,
            "report1_values": values1,
            "report2_file": alt_file if values2 else None,
            "report2_values": values2,
            "details": details
        })