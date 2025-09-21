# processors/day1_report_processor.py
import os, re, json
from .base import Processor, ProcessorResult
from PIL import Image

class Day1ReportProcessor(Processor):
    NAME = "day1_report"

    def _prompt(self) -> str:
        return """
Please analyze the Day_Report1 image and extract the following values:

1. Net sales total (labelled like 'Net Sales Total', 'Total Net Sales', or similar)
2. Credit amount from cashier details (exclude MOP sales)
3. Debit amount from cashier details (exclude MOP sales)

Respond with a JSON object like:
{
  "net_sales_total": 1234.56,
  "credit": 567.89,
  "debit": 123.45
}
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

    def _extract_with_gemini(self, image_path):
        prompt = self._prompt()
        resp = self.gemini.generate_from_image(prompt, image_path)
        if "error" in resp:
            return {"error": resp["error"]}
        text = resp.get("text", "")
        parsed = self._parse_json_from_text(text) or {"raw_text": text}
        return parsed

    def _extract_with_ocr(self, image_path):
        try:
            import pytesseract
            txt = pytesseract.image_to_string(Image.open(image_path))

            # Parse net sales
            net_sales = None
            m = re.search(r'Net Sales Total[:\s\$]*([\d,]+\.\d{1,2})', txt, re.IGNORECASE)
            if m:
                net_sales = float(m.group(1).replace(",", ""))

            # Parse credit
            credit = None
            m2 = re.search(r'Credit[:\s\$]*([\d,]+\.\d{1,2})', txt, re.IGNORECASE)
            if m2:
                credit = float(m2.group(1).replace(",", ""))

            # Parse debit
            debit = None
            m3 = re.search(r'Debit[:\s\$]*([\d,]+\.\d{1,2})', txt, re.IGNORECASE)
            if m3:
                debit = float(m3.group(1).replace(",", ""))

            return {
                "net_sales_total": net_sales,
                "credit": credit,
                "debit": debit,
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
        if "error" in parsed:
            # fallback to OCR
            parsed = self._extract_with_ocr(image_path)

        if dry_run:
            return ProcessorResult(self.NAME, True, {"parsed": parsed})

        # Write to Excel
        if not self.excel.load_template(specific_day):
            return ProcessorResult(self.NAME, False, {"error": "could not load template"})

        if isinstance(parsed, dict):
            net = parsed.get("net_sales_total")
            credit = parsed.get("credit")
            debit = parsed.get("debit")

            if net is not None:
                self.excel.sheet["L7"] = net
            if credit is not None:
                self.excel.sheet["I12"] = credit
            if debit is not None:
                self.excel.sheet["I13"] = debit

        saved = self.excel.save_report(self.excel.template_path)
        return ProcessorResult(self.NAME, success=saved, details={"parsed": parsed})
