# processors/lotto_processor.py
import os, re, json
from .base import Processor, ProcessorResult
from PIL import Image

class LottoProcessor(Processor):
    NAME = "lotto"

    def _prompt(self) -> str:
        return """
Please analyze this Lotto Machine Report image and extract the following specific values:

1. Look for "DRW GM NET SALES" (or "DRAW GM NET SALES") and get the dollar amount after it
2. Look for "DRW GM CASHES" (or "DRAW GM CASHES") and get the dollar amount after it  
3. Look for "SCRATCH CASHES" and get the dollar amount after it

IMPORTANT:
- Include decimal points (38.50 not 3850)
- Remove $ and negative signs but keep decimals

Respond with a JSON object like:
{
  "drw_gm_net_sales": 38.50,
  "drw_gm_cashes": 2.00,
  "scratch_cashes": 122.00
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

    def run(self, specific_day=None, dry_run: bool = False) -> ProcessorResult:
        image_path = self.config.get("image_path")
        if not image_path or not os.path.exists(image_path):
            return ProcessorResult(self.NAME, False, {"error":"image missing", "image_path": image_path})

        prompt = self._prompt()
        resp = self.gemini.generate_from_image(prompt, image_path)
        if "error" in resp:
            return ProcessorResult(self.NAME, False, {"error": resp["error"]})

        text = resp.get("text","")
        parsed = self._parse_json_from_text(text) or {"raw_text": text}

        if dry_run:
            return ProcessorResult(self.NAME, True, {"parsed": parsed})

        # Write to Excel
        if not self.excel.load_template(specific_day):
            return ProcessorResult(self.NAME, False, {"error":"could not load template"})

        # Map fields to cells (same as original)
        if isinstance(parsed, dict):
            net = parsed.get("drw_gm_net_sales")
            if net is not None:
                self.excel.sheet["T30"] = net
            # total cashes prefer explicit sum if present else compute
            drw = parsed.get("drw_gm_cashes")
            scratch = parsed.get("scratch_cashes")
            if parsed.get("total_cashes") is not None:
                self.excel.sheet["Z9"] = parsed.get("total_cashes")
            elif drw is not None and scratch is not None:
                try:
                    self.excel.sheet["Z9"] = float(drw) + float(scratch)
                except Exception:
                    pass

        saved = self.excel.save_report(self.excel.template_path)
        return ProcessorResult(self.NAME, success=saved, details={"parsed": parsed})
