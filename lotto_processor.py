import pytesseract
import cv2
import re
from excel_handler import ExcelHandler

class LottoMachineProcessor:
    def __init__(self):
        """Initialize Lotto Machine Report processor"""
        # Set Tesseract path
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
    def preprocess_image(self, image_path):
        """Preprocess image for better OCR"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                print(f"✗ Could not load image: {image_path}")
                return None
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Threshold for better text recognition
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return thresh
        except Exception as e:
            print(f"✗ Error preprocessing image: {e}")
            return None
    
    def extract_lotto_values(self, image_path):
        """Extract specific values from Lotto Machine Report"""
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image_path)
            if processed_image is None:
                return None
            
            # Extract text
            text = pytesseract.image_to_string(processed_image)
            print("Extracted text from Lotto Machine Report:")
            print("=" * 60)
            print(text)
            print("=" * 60)
            
            # Find the three values we need
            drw_gm_net_sales = self.find_drw_gm_net_sales(text)
            drw_gm_cashes = self.find_drw_gm_cashes(text)
            scratch_cashes = self.find_scratch_cashes(text)
            
            # Calculate sum of cashes
            total_cashes = None
            if drw_gm_cashes is not None and scratch_cashes is not None:
                total_cashes = drw_gm_cashes + scratch_cashes
                print(f"✓ Total Cashes (DRW GM + SCRATCH): {total_cashes}")
            
            return {
                'drw_gm_net_sales': drw_gm_net_sales,
                'drw_gm_cashes': drw_gm_cashes,
                'scratch_cashes': scratch_cashes,
                'total_cashes': total_cashes
            }
            
        except Exception as e:
            print(f"✗ Error extracting lotto values: {e}")
            return None
    
    def find_drw_gm_net_sales(self, text):
        """Find DRW GM NET SALES value"""
        patterns = [
            r'DRW\s+GM\s+NET\s+SALES[:\s]*([0-9,]+\.?[0-9]*)',
            r'DRW GM NET SALES[:\s]*([0-9,]+\.?[0-9]*)',
            r'NET\s+SALES[:\s]*([0-9,]+\.?[0-9]*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).replace(',', '')
                print(f"✓ Found DRW GM NET SALES: {value}")
                return float(value)
        
        print("✗ Could not find DRW GM NET SALES")
        return None
    
    def find_drw_gm_cashes(self, text):
        """Find DRW GM CASHES value"""
        patterns = [
            r'DRW\s+GM\s+CASHES[:\s]*([0-9,]+\.?[0-9]*)',
            r'DRW GM CASHES[:\s]*([0-9,]+\.?[0-9]*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).replace(',', '')
                print(f"✓ Found DRW GM CASHES: {value}")
                return float(value)
        
        print("✗ Could not find DRW GM CASHES")
        return None
    
    def find_scratch_cashes(self, text):
        """Find SCRATCH CASHES value"""
        patterns = [
            r'SCRATCH\s+CASHES[:\s]*([0-9,]+\.?[0-9]*)',
            r'SCRATCH CASHES[:\s]*([0-9,]+\.?[0-9]*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).replace(',', '')
                print(f"✓ Found SCRATCH CASHES: {value}")
                return float(value)
        
        print("✗ Could not find SCRATCH CASHES")
        return None
    
    def process_and_update_excel(self, image_path, specific_day=None):
        """Extract values from image and update Excel file"""
        print("Processing Lotto Machine Report...")
        
        # Extract values from image
        values = self.extract_lotto_values(image_path)
        if not values:
            print("✗ Failed to extract values from image")
            return False
        
        # Update Excel file
        excel = ExcelHandler()
        if not excel.load_template(specific_day):
            print("✗ Failed to load Excel template")
            return False
        
        # Update the values in Excel
        if values['drw_gm_net_sales']:
            excel.sheet['T30'] = values['drw_gm_net_sales']  # Lotto M/C Net Sales
            print(f"✓ Updated T30 (Lotto M/C Net Sales): {values['drw_gm_net_sales']}")
        
        if values['total_cashes']:
            excel.sheet['Z9'] = values['total_cashes']  # Sum of cashes
            print(f"✓ Updated Z9 (Total Cashes): {values['total_cashes']}")
        
        # Save the file
        filename = f"lotto_updated_day{excel.current_day}.xlsx"
        excel.save_report(filename)
        
        print(f"\n✓ Lotto Machine Report processed successfully!")
        return True

# Test the processor
if __name__ == "__main__":
    print("Testing Lotto Machine Processor...")
    
    # Update this with your actual image filename
    test_image = "sample_report.jpg"
    
    processor = LottoMachineProcessor()
    processor.process_and_update_excel(test_image)