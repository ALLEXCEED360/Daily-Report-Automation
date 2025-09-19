import os
import google.generativeai as genai
from PIL import Image
import json
import re
from datetime import datetime, timedelta
from excel_handler import ExcelHandler

class CompleteLottoProcessor:
    def __init__(self, gemini_api_key):
        """Initialize the complete lotto processor"""
        # Setup Gemini Vision
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def extract_lotto_data(self, image_path):
        """Extract specific lotto data using Gemini Vision"""
        try:
            # Load image
            image = Image.open(image_path)
            print("📷 Analyzing lotto machine report with Gemini Vision...")
            
            # Create the prompt for extracting lotto data
            prompt = """
            Please analyze this Lotto Machine Report image and extract the following specific values:

            1. Look for "DRW GM NET SALES" (or "DRAW GM NET SALES") and get the dollar amount after it
            2. Look for "DRW GM CASHES" (or "DRAW GM CASHES") and get the dollar amount after it  
            3. Look for "SCRATCH CASHES" and get the dollar amount after it

            IMPORTANT: 
            - Include decimal points in your response (e.g., if you see $38.50, return 38.50 not 3850)
            - Remove dollar signs and any negative signs, but keep decimal points
            - If a value shows as $122.00-, just return 122.00

            Please respond in this exact JSON format:
            {
                "drw_gm_net_sales": [number with decimals or null if not found],
                "drw_gm_cashes": [number with decimals or null if not found], 
                "scratch_cashes": [number with decimals or null if not found],
                "total_cashes": [sum of drw_gm_cashes + scratch_cashes or null]
            }
            """
            
            # Send request to Gemini
            response = self.model.generate_content([prompt, image])
            result_text = response.text
            
            print("🤖 Gemini Response:")
            print(result_text)
            
            # Try to parse as JSON
            try:
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    result_json = json.loads(json_str)
                    
                    # Calculate total_cashes if not provided
                    if result_json.get('drw_gm_cashes') and result_json.get('scratch_cashes'):
                        if not result_json.get('total_cashes'):
                            result_json['total_cashes'] = result_json['drw_gm_cashes'] + result_json['scratch_cashes']
                    
                    return result_json
                else:
                    print("⚠️ No JSON found in response")
                    return None
                    
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parsing error: {e}")
                return None
                
        except Exception as e:
            print(f"✗ Error with Gemini Vision: {e}")
            return None
    
    def process_lotto_report_to_excel(self, image_path, specific_day=None):
        """Complete process: Extract from image and update Excel"""
        print("=" * 60)
        print("🎰 PROCESSING LOTTO MACHINE REPORT")
        print("=" * 60)
        
        # Step 1: Extract data from image
        print("Step 1: Extracting data from image...")
        extracted_data = self.extract_lotto_data(image_path)
        
        if not extracted_data:
            print("❌ Failed to extract data from image")
            return False
        
        # Step 2: Load Excel template
        print("\nStep 2: Loading Excel template...")
        excel = ExcelHandler()
        # If no specific_day provided, choose yesterday's day number (user requested processing previous day's report)
        if specific_day is None:
            yesterday = datetime.now() - timedelta(days=1)
            specific_day = yesterday.day
            print(f"ℹ️ No specific_day provided — defaulting to yesterday: {yesterday.strftime('%Y-%m-%d')} (sheet '{specific_day}')")
        if not excel.load_template(specific_day):
            print("❌ Failed to load Excel template")
            return False
        
        # Step 3: Update Excel with extracted data
        print("\nStep 3: Updating Excel template...")
        
        # Update Lotto M/C Net Sales at T30
        if extracted_data.get('drw_gm_net_sales'):
            excel.sheet['T30'] = extracted_data['drw_gm_net_sales']
            print(f"✅ Updated T30 (Lotto M/C Net Sales): ${extracted_data['drw_gm_net_sales']}")
        else:
            print("⚠️ DRW GM NET SALES not found, skipping T30 update")
        
        # Update total cashes at Z9
        if extracted_data.get('total_cashes'):
            excel.sheet['Z9'] = extracted_data['total_cashes']
            print(f"✅ Updated Z9 (Total Cashes): ${extracted_data['total_cashes']}")
            print(f"   (Sum of DRW GM CASHES: ${extracted_data.get('drw_gm_cashes', 0)} + SCRATCH CASHES: ${extracted_data.get('scratch_cashes', 0)})")
        else:
            print("⚠️ Could not calculate total cashes, skipping Z9 update")
        
        # Step 4: Save the updated file (overwrite the template if possible)
        print("\nStep 4: Saving updated Excel file...")
        # Prefer to overwrite the template if ExcelHandler exposes the original template path
        out_filename = None
        if hasattr(excel, 'template_path') and excel.template_path:
            out_filename = excel.template_path
            print(f"ℹ️ Overwriting template file: {out_filename}")
        else:
            today = excel.current_day
            out_filename = f"lotto_updated_day_{today}.xlsx"
            print(f"⚠️ ExcelHandler has no template_path attribute; saving to {out_filename} instead")
        
        if excel.save_report(out_filename):
            print(f"✅ Successfully saved (overwrote): {out_filename}")
            print("\n" + "=" * 60)
            print("🎉 LOTTO REPORT PROCESSING COMPLETE!")
            print("=" * 60)
            print("Summary of updates:")
            # Use displayed sheet name if available
            sheet_display = getattr(excel, 'current_day', specific_day)
            print(f"  • Sheet: {sheet_display}")
            print(f"  • T30 (Lotto M/C Net Sales): ${extracted_data.get('drw_gm_net_sales', 'N/A')}")
            print(f"  • Z9 (Total Cashes): ${extracted_data.get('total_cashes', 'N/A')}")
            print(f"  • File saved as: {out_filename}")
            return True
        else:
            print("❌ Failed to save Excel file")
            return False

# Test function
def test_complete_processor():
    # Read Gemini API key from environment variable
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("❌ No GEMINI_API_KEY found in environment. Set GEMINI_API_KEY and re-run.")
    
    # Create processor
    processor = CompleteLottoProcessor(api_key)
    
    # Process the lotto report image and update Excel (by default uses yesterday's sheet and overwrites template)
    success = processor.process_lotto_report_to_excel("Others\sample_report.jpg")
    
    if success:
        print("\n🎊 Test completed successfully!")
        print("Check the template file to verify the updates.")
    else:
        print("\n❌ Test failed!")

if __name__ == "__main__":
    print("Testing Complete Lotto Processor...")
    test_complete_processor()
