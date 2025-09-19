import pytesseract
import cv2
import numpy as np
from PIL import Image
import re

class OCRHandler:
    def __init__(self):
        """Initialize OCR handler"""
        # Set Tesseract path (update this if your path is different)
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    def preprocess_image(self, image_path):
        """Preprocess image to improve OCR accuracy"""
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                print(f"✗ Could not load image: {image_path}")
                return None
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply noise reduction
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Apply threshold to get better contrast
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            print("✓ Image preprocessed successfully")
            return thresh
            
        except Exception as e:
            print(f"✗ Error preprocessing image: {e}")
            return None
    
    def extract_text_from_image(self, image_path, save_processed=False):
        """Extract text from image using OCR"""
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image_path)
            if processed_image is None:
                return None
            
            # Save processed image if requested (for debugging)
            if save_processed:
                cv2.imwrite('processed_image.jpg', processed_image)
                print("✓ Processed image saved as 'processed_image.jpg'")
            
            # Extract text using OCR
            text = pytesseract.image_to_string(processed_image)
            
            print("✓ Text extracted from image")
            print("=" * 50)
            print("EXTRACTED TEXT:")
            print("=" * 50)
            print(text)
            print("=" * 50)
            
            return text
            
        except Exception as e:
            print(f"✗ Error extracting text: {e}")
            return None
    
    def find_value_after_text(self, text, search_term):
        """Find a number that appears after specific text"""
        try:
            # Create pattern to find the search term followed by numbers
            pattern = rf'{re.escape(search_term)}[:\s]*([0-9,]+\.?[0-9]*)'
            match = re.search(pattern, text, re.IGNORECASE)
            
            if match:
                value = match.group(1).replace(',', '')  # Remove commas
                print(f"✓ Found '{search_term}': {value}")
                return float(value) if '.' in value else int(value)
            else:
                print(f"✗ Could not find '{search_term}' in text")
                return None
                
        except Exception as e:
            print(f"✗ Error finding value: {e}")
            return None

# Test the OCR handler
if __name__ == "__main__":
    print("Testing OCR Handler...")
    print("This test requires a sample image file.")
    print("Please add a photo of one of your reports to the project folder and update the filename below.")
    
    # You'll need to add a test image and update this filename
    test_image = "sample_report.jpg"  # Change this to your actual image filename
    
    ocr = OCRHandler()
    
    # Test text extraction
    text = ocr.extract_text_from_image(test_image, save_processed=True)
    
    if text:
        # Test finding specific values
        print("\nTesting value extraction...")
        ocr.find_value_after_text(text, "NET SALES")
        ocr.find_value_after_text(text, "TOTAL")
    else:
        print("Could not extract text - make sure you have a test image file")