import { NextRequest, NextResponse } from 'next/server';
import { GoogleGenerativeAI } from '@google/generative-ai';
import XlsxPopulate from 'xlsx-populate';
import { promises as fs } from 'fs';
import path from 'path';

// Parse currency-like values from text (similar to Python implementation)
function parseCurrencyLike(text: string): number | null {
  if (!text) {
    return null;
  }

  // Normalize spacing
  const txt = text.replace(/\n/g, ' ').replace(/\r/g, ' ');

  // 1) Look for patterns like "EBT ... 1,234.56" or "EBT: $123.45" or "EBT TOTAL 123.45"
  let match = txt.match(/EBT[^0-9\.\-]*([\$\-]?\s*\d{1,3}(?:[,]\d{3})*(?:\.\d{1,2})?)/i);
  if (match) {
    const numstr = match[1];
    return toFloat(numstr);
  }

  // 2) Look for "EBT" and a number after it within 60 chars
  match = txt.match(/EBT(.{0,60}?)([\$\-]?\s*\d{1,3}(?:[,]\d{3})*(?:\.\d{1,2})?)/i);
  if (match) {
    return toFloat(match[2]);
  }

  // 3) If a "TOTAL" appears near "EBT", capture a number near "TOTAL"
  match = txt.match(/(?:EBT.*?TOTAL|TOTAL.*?EBT)(.{0,60}?)([\$\-]?\s*\d{1,3}(?:[,]\d{3})*(?:\.\d{1,2})?)/i);
  if (match) {
    return toFloat(match[2]);
  }

  // 4) As a last resort, capture the first currency-like number in text
  match = txt.match(/([\$\-]?\s*\d{1,3}(?:[,]\d{3})*(?:\.\d{1,2})?)/);
  if (match) {
    return toFloat(match[1]);
  }

  return null;
}

function toFloat(s: string): number | null {
  if (!s) {
    return null;
  }
  s = s.replace(/\$/g, '').replace(/\s/g, '').replace(/\u200b/g, '');
  // handle trailing dash like '122.00-'
  s = s.replace(/-$/, '');
  s = s.replace(/,/g, '');
  try {
    return parseFloat(s);
  } catch {
    return null;
  }
}

function toNum(x: any): number {
  try {
    if (x === null || x === undefined) {
      return 0.0;
    }
    if (typeof x === 'number') {
      return x;
    }
    // string: remove non-numeric
    const s = String(x).replace(/\$/g, '').replace(/,/g, '').trim();
    return s !== '' ? parseFloat(s) : 0.0;
  } catch {
    return 0.0;
  }
}

export async function POST(request: NextRequest) {
  try {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      return NextResponse.json(
        { error: 'GEMINI_API_KEY environment variable not set' },
        { status: 500 }
      );
    }

    const formData = await request.formData();
    const file = formData.get('image') as File;
    const dayNumberStr = formData.get('dayNumber') as string;

    if (!file) {
      return NextResponse.json(
        { error: 'No image file provided' },
        { status: 400 }
      );
    }

    if (!dayNumberStr) {
      return NextResponse.json(
        { error: 'Day number (1-31) is required' },
        { status: 400 }
      );
    }

    const dayNumber = parseInt(dayNumberStr, 10);
    if (isNaN(dayNumber) || dayNumber < 1 || dayNumber > 31) {
      return NextResponse.json(
        { error: 'Day number must be between 1 and 31' },
        { status: 400 }
      );
    }

    // Convert file to base64
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);
    const base64Image = buffer.toString('base64');
    const mimeType = file.type || 'image/jpeg';

    // Initialize Gemini
    const genAI = new GoogleGenerativeAI(apiKey);
    const model = genAI.getGenerativeModel({ model: 'gemini-2.5-flash' });

    // Prepare the prompt (same as Python version)
    const prompt = `
Please analyze this Batch Report image and return the dollar amount that corresponds to the EBT total.
Look for lines containing the word 'EBT' (or 'E B T') and a dollar amount or the word 'Total' near EBT.
Return a short line such as: EBT: 123.45
If you cannot find an EBT amount, return NOT_FOUND.
`;

    // Generate content from image
    const result = await model.generateContent([
      prompt,
      {
        inlineData: {
          data: base64Image,
          mimeType: mimeType,
        },
      },
    ]);

    const response = result.response;
    const text = response.text();

    // Parse the EBT value from the response
    const extractedValue = parseCurrencyLike(text);

    if (extractedValue === null) {
      return NextResponse.json({
        success: false,
        error: 'EBT not found',
        raw: text,
        details: {
          gemini: { value: null, raw: text },
        },
      });
    }

    // Handle Excel writing
    try {
      // Get path to original Excel file
      const excelPath = path.join(process.cwd(), 'public', 'daily_report_template.xlsx');

      // Read the Excel file with xlsx-populate (preserves formatting, tables, filters, etc.)
      const workbook = await XlsxPopulate.fromFileAsync(excelPath);

      // Select sheet by day number
      // Try by name first (sheet names might be "1", "2", "3", etc.)
      let sheetName = String(dayNumber);
      let worksheet = workbook.sheet(sheetName);
      
      // If not found by name, try by index (1-based)
      if (!worksheet && dayNumber > 0 && dayNumber <= workbook.sheets().length) {
        worksheet = workbook.sheet(dayNumber - 1);
        if (worksheet) {
          sheetName = worksheet.name();
        }
      }
      
      // If still not found, try exact match with sheet names
      if (!worksheet) {
        const sheets = workbook.sheets();
        const matchingSheet = sheets.find((ws: any, index: number) => {
          const name = ws.name();
          return name === String(dayNumber) || name === `Sheet${dayNumber}` || name === `Day ${dayNumber}`;
        });
        if (matchingSheet) {
          worksheet = matchingSheet;
          sheetName = worksheet.name();
        }
      }
      
      if (!worksheet) {
        const availableSheets = workbook.sheets().map((ws: any) => ws.name()).join(', ');
        return NextResponse.json({
          success: false,
          error: `Sheet for day ${dayNumber} not found. Available sheets: ${availableSheets}`,
          extracted_ebt: extractedValue,
          raw: text,
        });
      }

      // Read existing value in Z10 (for display purposes only)
      const z10Cell = worksheet.cell('Z10');
      const currentValue = z10Cell.value();
      const currentNum = toNum(currentValue);

      // Overwrite with extracted value (don't add, just replace)
      z10Cell.value(extractedValue);

      // Save back to the original file (preserves all formatting, formulas, tables, filters, etc.)
      await workbook.toFileAsync(excelPath);

      return NextResponse.json({
        success: true,
        extracted_ebt: extractedValue,
        previous_Z10: currentNum,
        new_Z10: extractedValue,
        sheet: sheetName,
        raw: text,
        details: {
          gemini: { value: extractedValue, raw: text },
        },
      });
    } catch (excelError: any) {
      console.error('Error writing to Excel:', excelError);
      return NextResponse.json({
        success: false,
        error: `Failed to write to Excel: ${excelError.message}`,
        extracted_ebt: extractedValue,
        raw: text,
        details: {
          gemini: { value: extractedValue, raw: text },
        },
      });
    }
  } catch (error: any) {
    console.error('Error processing batch image:', error);
    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Failed to process image',
      },
      { status: 500 }
    );
  }
}

