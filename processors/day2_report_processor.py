# processors/day2_report_processor.py
import os
import re
import json
from .base import Processor, ProcessorResult
from PIL import Image

class Day2ReportProcessor(Processor):
    NAME = "day2_report"

    def _prompt(self) -> str:
        return """
Please analyze this Day Report page image and extract values from the Category Report section and the Tax Report section.

From the Category Report (look for labels like 'LOTTERY', 'Lottery', 'lottery'):
 - Return the net sales value for LOTTERY.

From the Category Report (look for labels like 'Fuel deposit', 'fuel deposit', 'Fuel Deposit'):
 - Return the fuel deposit net sales value.

From the Tax Report section:
 - Return the TAXABLE-SALES value (labelled 'TAXABLE-SALES', 'Taxable Sales', or similar).
 - Return the TAXES value (labelled 'TAXES', 'Sales Tax', or similar).

Return a JSON object like:
{
  "lottery_net": 38.50,
  "fuel_deposit": 1234.56,
  "taxable_sales": 9876.54,
  "taxes": 123.45
}
If a value is not found, keep it null.
"""

    def _parse_json_from_text(self, text: str):
        if not text:
            return None
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                return None
        return None

    def _to_float(self, s):
        if s is None:
            return None
        s = str(s).replace("$", "").replace(",", "").strip()
        s = s.rstrip("-")
        try:
            return float(s)
        except Exception:
            return None

    def _extract_numbers_near_labels(self, text):
        """
        Return dict with keys: lottery_net, fuel_deposit, taxable_sales, taxes
        Attempt multiple label variants, robust to spacing and separators.
        """
        out = {"lottery_net": None, "fuel_deposit": None, "taxable_sales": None, "taxes": None}
        if not text:
            return out

        txt = " ".join(text.split())

        def find_near(labels):
            for label in labels:
                pattern = rf'{re.escape(label)}[^0-9\-\$]{{0,60}}([\$\-]?\s*\d{{1,3}}(?:[,]\d{{3}})*(?:\.\d{{1,2}})?)'
                m = re.search(pattern, txt, re.IGNORECASE)
                if m:
                    val = self._to_float(m.group(1))
                    if val is not None:
                        return val
                pattern2 = rf'([\$\-]?\s*\d{{1,3}}(?:[,]\d{{3}})*(?:\.\d{{1,2}})?)[^0-9\-\$]{{0,60}}{re.escape(label)}'
                m2 = re.search(pattern2, txt, re.IGNORECASE)
                if m2:
                    val = self._to_float(m2.group(1))
                    if val is not None:
                        return val
            return None

        out["lottery_net"] = find_near(["LOTTERY", "Lottery", "lottery", "Category lottery", "Lottery Net", "Lottery Net Sales", "Lotto"])
        out["fuel_deposit"] = find_near(["Fuel deposit", "fuel deposit", "Fuel Deposit", "Fuel deposit net", "Fuel deposit sales"])
        out["taxable_sales"] = find_near(["TAXABLE-SALES", "Taxable Sales", "Taxable_Sales", "Taxable-sales", "Taxable"])
        out["taxes"] = find_near(["TAXES", "Taxes", "Sales Tax", "Tax"])

        return out

    def _extract_with_gemini(self, image_path):
        prompt = self._prompt()
        resp = self.gemini.generate_from_image(prompt, image_path)
        if "error" in resp:
            return {"error": resp["error"]}
        text = resp.get("text", "")
        parsed_json = self._parse_json_from_text(text)
        if parsed_json:
            return {
                "lottery_net": self._to_float(parsed_json.get("lottery_net") or parsed_json.get("lottery") or parsed_json.get("lottery_net_sales")),
                "fuel_deposit": self._to_float(parsed_json.get("fuel_deposit") or parsed_json.get("fuel_deposit_net") or parsed_json.get("fuel_deposit_sales")),
                "taxable_sales": self._to_float(parsed_json.get("taxable_sales") or parsed_json.get("taxable-sales") or parsed_json.get("taxable")),
                "taxes": self._to_float(parsed_json.get("taxes") or parsed_json.get("tax"))
            }
        parsed = self._extract_numbers_near_labels(text)
        parsed["raw_text"] = text
        return parsed

    def _extract_with_ocr(self, image_path):
        try:
            import pytesseract
            txt = pytesseract.image_to_string(Image.open(image_path))
            parsed = self._extract_numbers_near_labels(txt)
            parsed["raw_text"] = txt
            return parsed
        except Exception as e:
            return {"error": f"pytesseract error: {e}"}

    def run(self, specific_day=None, dry_run: bool = False) -> ProcessorResult:
        image_path = self.config.get("image_path")
        if not image_path or not os.path.exists(image_path):
            return ProcessorResult(self.NAME, False, {"error": "image missing", "image_path": image_path})

        parsed = self._extract_with_gemini(image_path)
        details = {"gemini": parsed if isinstance(parsed, dict) else {"raw": parsed}}

        if (isinstance(parsed, dict) and all(parsed.get(k) is None for k in ("lottery_net", "fuel_deposit", "taxable_sales", "taxes"))):
            ocr_parsed = self._extract_with_ocr(image_path)
            details["ocr"] = ocr_parsed
            for k in ("lottery_net", "fuel_deposit", "taxable_sales", "taxes"):
                if (parsed.get(k) is None) and isinstance(ocr_parsed, dict):
                    parsed[k] = ocr_parsed.get(k)

        if dry_run:
            return ProcessorResult(self.NAME, True, {"parsed": parsed, "details": details})

        if not self.excel.load_template(specific_day):
            return ProcessorResult(self.NAME, False, {"error": "could not load template", "details": details})

        if parsed.get("lottery_net") is not None:
            self.excel.sheet["L6"] = parsed.get("lottery_net")
        if parsed.get("fuel_deposit") is not None:
            self.excel.sheet["F15"] = parsed.get("fuel_deposit")
        if parsed.get("taxable_sales") is not None:
            self.excel.sheet["F16"] = parsed.get("taxable_sales")
        if parsed.get("taxes") is not None:
            self.excel.sheet["F17"] = parsed.get("taxes")
            self.excel.sheet["Z11"] = parsed.get("taxes")   # 👈 new line to also write to Z11

        saved = self.excel.save_report(self.excel.template_path)
        return ProcessorResult(self.NAME, success=saved, details={"parsed": parsed, "details": details})
