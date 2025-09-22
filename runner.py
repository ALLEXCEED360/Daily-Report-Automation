# runner.py
import os
import argparse
from handlers.gemini_handler import GeminiVisionHandler
from handlers.excel_handler import ExcelHandler
from processors.lotto_processor import LottoProcessor
from processors.shift_processor import ShiftProcessor
from processors.batch_processor import BatchProcessor
from processors.day1_report_processor import Day1ReportProcessor
from processors.day2_report_processor import Day2ReportProcessor
from processors.day3_report_processor import Day3ReportProcessor
from processors.handwritten_processor import HandwrittenProcessor


def main():
    parser = argparse.ArgumentParser(description="Run processors to extract report data and update Excel.")
    parser.add_argument("--day", help="Specific day sheet or YYYY-MM-DD to process (optional).", default=None)
    parser.add_argument("--dry-run", help="Parse and show values but do not save Excel.", action="store_true")
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable not set.")

    gemini = GeminiVisionHandler(api_key)
    excel = ExcelHandler()

    base = os.path.dirname(os.path.abspath(__file__))
    others = os.path.join(base, "Others")

    processors = [
    Day1ReportProcessor(gemini, excel, config={"image_path": os.path.join(others, "Day_Report1.jpg")}),
    Day2ReportProcessor(gemini, excel, config={"image_path": os.path.join(others, "Day_Report2.jpg")}),
    Day3ReportProcessor(gemini, excel, config={"image_path": os.path.join(others, "Day_Report3.jpg")}),
    HandwrittenProcessor(gemini, excel, config={"image_path": os.path.join(others, "Handwritten_Report.jpg")}),
    LottoProcessor(gemini, excel, config={"image_path": os.path.join(others, "sample_report.jpg")}),
    ShiftProcessor(gemini, excel, config={"others_dir": others}),
    BatchProcessor(gemini, excel, config={"image_path": os.path.join(others, "batch_report.jpg")}),
]


    for p in processors:
        print("\n" + "="*50)
        print(f"Running processor: {p.__class__.__name__}")
        res = p.run(specific_day=args.day, dry_run=args.dry_run)
        print(f"Result: {res}")

if __name__ == "__main__":
    main()
