# Test script to verify all installations work
print("Testing Python setup...")

try:
    import openpyxl
    print("✓ openpyxl installed correctly")
except ImportError:
    print("✗ openpyxl not found")

try:
    import pandas as pd
    print("✓ pandas installed correctly")
except ImportError:
    print("✗ pandas not found")

try:
    import pytesseract
    print("✓ pytesseract installed correctly")
except ImportError:
    print("✗ pytesseract not found")

try:
    from PIL import Image
    print("✓ PIL (Pillow) installed correctly")
except ImportError:
    print("✗ PIL not found")

try:
    import cv2
    print("✓ opencv installed correctly")
except ImportError:
    print("✗ opencv not found")

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
try:
    # For Windows users - you might need to set this path
    # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    version = pytesseract.get_tesseract_version()
    print(f"✓ Tesseract OCR working - version: {version}")
except Exception as e:
    print(f"✗ Tesseract OCR issue: {e}")

print("\nSetup test complete!")