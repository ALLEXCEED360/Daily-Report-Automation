# Daily Report Automation

A Next.js web application that automates the extraction of data from daily report images using Google Gemini AI and populates an Excel template automatically. This tool processes various types of reports including batch reports, day reports, handwritten reports, lotto machine reports, and shift reports.

## Features

- 🤖 **AI-Powered Data Extraction**: Uses Google Gemini AI to extract data from report images
- 📊 **Multiple Report Processors**: Supports 8 different report types:
  - **Batch Report**: Extracts EBT totals
  - **Day 1 Report**: Extracts Net Sales Total, Credit, and Debit
  - **Day 2 Report**: Extracts Lottery Net, Fuel Deposit, Taxable Sales, and Taxes
  - **Day 3 Report**: Extracts product volumes (Unleaded, Plus, Premium, Diesel)
  - **Handwritten Report**: Extracts shift counts, Total Cash, Additional sum, and Game in/out values
  - **Lotto Machine Report**: Extracts DRW GM Net Sales, DRW GM Cashes, and Scratch Cashes
  - **Shift Report**: Extracts customer counts from Morning, Evening, and Night shifts
  - **Handwritten Lotto End**: Extracts End no values from handwritten reports
- 📁 **Excel Template Management**: 
  - Upload new Excel templates to replace the existing one
  - Download the updated Excel file with extracted data
  - Preserves formatting, formulas, tables, and filters
- 🎨 **Modern UI**: Built with Next.js, TypeScript, Tailwind CSS, and Radix UI components
- 📱 **Responsive Design**: Works on desktop and mobile devices

## Prerequisites

- Node.js 18+ and npm
- Google Gemini API key (set as `GEMINI_API_KEY` environment variable)

## Getting Started

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd report_automation
```

2. Install dependencies:
```bash
npm install
```

3. Set up environment variables:
Create a `.env.local` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

4. Place your Excel template:
Ensure `public/daily_report_template.xlsx` exists with sheets numbered 1-31 (or named accordingly).

### Development

Run the development server:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Building for Production

```bash
npm run build
npm start
```

## Usage

1. **Enter Day Number**: Input a day number (1-31) that corresponds to the sheet in your Excel file
2. **Select Report Type**: Choose the appropriate tab for the type of report you're processing
3. **Upload Image**: Upload an image of the report (supports multiple images for some processors)
4. **Process**: Click "Process & Save to Excel" to extract data and save it to the Excel template
5. **Download**: Download the updated Excel file with all extracted data
6. **Update Template**: Upload a new Excel template file to replace the current one

## Project Structure

```
report_automation/
├── app/
│   ├── api/
│   │   ├── download-excel/     # Download Excel file endpoint
│   │   ├── process/            # Main processing endpoint
│   │   ├── process-batch/      # Batch report processor
│   │   ├── process-shift/     # Shift report processor
│   │   └── upload-excel/       # Upload Excel template endpoint
│   ├── page.tsx                # Main application page
│   └── globals.css             # Global styles
├── components/
│   └── ui/                     # Reusable UI components
├── lib/
│   └── excel-utils.ts          # Excel manipulation utilities
├── types/
│   └── xlsx-populate.d.ts      # TypeScript declarations
├── public/
│   └── daily_report_template.xlsx  # Excel template file
└── package.json
```

## API Endpoints

### POST `/api/process`
Processes images and extracts data based on processor type.

**Body (FormData):**
- `image`: Image file (required)
- `image2`: Second image file (optional, for some processors)
- `processorType`: Type of processor (batch, day1, day2, day3, handwritten, lotto, handwritten_lotto_end)
- `dayNumber`: Day number (1-31)

### POST `/api/process-shift`
Processes shift report images.

**Body (FormData):**
- `morning`: Morning shift image (optional)
- `evening`: Evening shift image (optional)
- `night`: Night shift image (optional)
- `dayNumber`: Day number (1-31)

### POST `/api/upload-excel`
Uploads a new Excel template to replace the existing one.

**Body (FormData):**
- `file`: Excel file (.xlsx or .xls)

### GET `/api/download-excel`
Downloads the current Excel template file.

## Technologies Used

- **Next.js 16**: React framework with App Router
- **TypeScript**: Type-safe JavaScript
- **Google Gemini AI**: AI-powered image analysis
- **xlsx-populate**: Excel file manipulation
- **Tailwind CSS**: Utility-first CSS framework
- **Radix UI**: Accessible component primitives
- **Lucide React**: Icon library

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key for AI processing | Yes |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is private and proprietary.

## Support

For issues and questions, please open an issue in the repository.
