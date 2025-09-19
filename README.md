# Daily Reports Automation

Automates the extraction of Lotto Machine report data from images and updates an Excel template with the results.

## Overview

This project helps streamline the daily reporting process for Lotto Machine data. It uses **Google Gemini Vision** to extract relevant values from images of reports and updates an Excel template with the extracted data.

### Key Features

- Extracts **DRW GM NET SALES**, **DRW GM CASHES**, and **SCRATCH CASHES** from report images
- Calculates total cashes automatically
- Updates the Excel template with the extracted values
- Supports processing reports for previous days
- Designed to work with a `.xlsx` template file for easy integration

## Project Structure

```
├── complete_lotto_processor.py
├── gemini_handler.py
├── excel_handler.py
├── .gitignore
└── README.md
```

## Requirements

- **Python 3.10+**
- **Required Packages:**
  - `google-generativeai`
  - `Pillow`
  - `openpyxl`

### Install Dependencies

```bash
pip install google-generativeai Pillow openpyxl
```

## Setup

### 1. Google Gemini API Key

Set your API key as an environment variable:

**Linux/macOS:**
```bash
export GEMINI_API_KEY="YOUR_API_KEY"
```

**Windows (PowerShell):**
```powershell
setx GEMINI_API_KEY "YOUR_API_KEY"
```

### 2. Excel Template

Ensure `daily_report_template.xlsx` exists in the project directory.

> **Note:** This file is not tracked in Git for security purposes.

## Usage

```python
from complete_lotto_processor import CompleteLottoProcessor
import os

# Initialize processor with API key
api_key = os.environ.get("GEMINI_API_KEY")
processor = CompleteLottoProcessor(api_key)

# Process report image and update Excel template
processor.process_lotto_report_to_excel("sample_report.jpg")
```

### How It Works

1. The script extracts relevant values from the image using Google Gemini Vision
2. Updates the Excel template for the previous day by default
3. Saves changes by overwriting the template

## Security

- **API keys are never hardcoded** in the repository. Always use environment variables
- **Excel templates are ignored** in Git to avoid accidental sharing of sensitive data
- Follow best practices for handling sensitive business data

## File Descriptions

| File | Description |
|------|-------------|
| `complete_lotto_processor.py` | Main processor class that orchestrates the entire workflow |
| `gemini_handler.py` | Handles Google Gemini API interactions for image processing |
| `excel_handler.py` | Manages Excel file operations and template updates |
| `sample_report.jpg` | Example report image for testing |
| `.gitignore` | Excludes sensitive files from version control |

## Data Extracted

The system specifically looks for and extracts:

- **DRW GM NET SALES** - Daily net sales figures
- **DRW GM CASHES** - Daily cash transactions
- **SCRATCH CASHES** - Scratch ticket cash transactions
- **Total Cashes** - Automatically calculated sum of cash transactions

## Contributing

1. Ensure all sensitive data is properly excluded from commits
2. Use environment variables for all API keys and sensitive configuration
3. Test with sample data before processing real reports
4. Follow the existing code structure and naming conventions

## Troubleshooting

### Common Issues

- **API Key Not Found**: Ensure the `GEMINI_API_KEY` environment variable is set correctly
- **Excel Template Missing**: Verify `daily_report_template.xlsx` exists in the project directory
- **Image Processing Errors**: Check that the report image is clear and contains the expected data fields
- **Permission Errors**: Ensure the Excel template file is not open in another application

### Error Handling

The system includes error handling for:
- Missing or invalid API keys
- Corrupted or unreadable images
- Excel file access issues
- Network connectivity problems with the Gemini API
