import { NextRequest, NextResponse } from 'next/server';
import { GoogleGenerativeAI } from '@google/generative-ai';
import { loadExcelWorkbook, saveExcelWorkbook } from '@/lib/excel-utils';

function parseNumber(text: string): number | null {
  if (!text) return null;
  const match = text.match(/(?:#?\s*Customers?[:\s\-]*)(\d{1,6})/i);
  if (match) {
    try {
      return parseInt(match[1], 10);
    } catch {
      return null;
    }
  }
  const match2 = text.match(/\b(\d{1,6})\b/);
  if (match2) {
    try {
      return parseInt(match2[1], 10);
    } catch {
      return null;
    }
  }
  return null;
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
    const morningFile = formData.get('morning') as File;
    const eveningFile = formData.get('evening') as File;
    const nightFile = formData.get('night') as File;
    const dayNumberStr = formData.get('dayNumber') as string;

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

    const genAI = new GoogleGenerativeAI(apiKey);
    const model = genAI.getGenerativeModel({ model: 'gemini-2.5-flash' });
    const prompt = `Return only the number of customers found in this image, or the text 'NOT_FOUND' if none.
Look for '#Customers', 'Customers', 'No. of Customers', or similar.`;

    const results: any = { morning: null, evening: null, night: null, details: {} };

    // Process morning shift
    if (morningFile) {
      const morningBytes = await morningFile.arrayBuffer();
      const morningBuffer = Buffer.from(morningBytes);
      const morningBase64 = morningBuffer.toString('base64');
      const morningMime = morningFile.type || 'image/jpeg';
      const morningResult = await model.generateContent([prompt, { inlineData: { data: morningBase64, mimeType: morningMime } }]);
      const morningText = morningResult.response.text();
      results.morning = parseNumber(morningText);
      results.details.morning = { raw: morningText, value: results.morning };
    }

    // Process evening shift
    if (eveningFile) {
      const eveningBytes = await eveningFile.arrayBuffer();
      const eveningBuffer = Buffer.from(eveningBytes);
      const eveningBase64 = eveningBuffer.toString('base64');
      const eveningMime = eveningFile.type || 'image/jpeg';
      const eveningResult = await model.generateContent([prompt, { inlineData: { data: eveningBase64, mimeType: eveningMime } }]);
      const eveningText = eveningResult.response.text();
      results.evening = parseNumber(eveningText);
      results.details.evening = { raw: eveningText, value: results.evening };
    }

    // Process night shift
    if (nightFile) {
      const nightBytes = await nightFile.arrayBuffer();
      const nightBuffer = Buffer.from(nightBytes);
      const nightBase64 = nightBuffer.toString('base64');
      const nightMime = nightFile.type || 'image/jpeg';
      const nightResult = await model.generateContent([prompt, { inlineData: { data: nightBase64, mimeType: nightMime } }]);
      const nightText = nightResult.response.text();
      results.night = parseNumber(nightText);
      results.details.night = { raw: nightText, value: results.night };
    }

    // Write to Excel
    const { workbook, worksheet } = await loadExcelWorkbook(dayNumber);
    if (results.morning != null) worksheet.cell('E10').value(results.morning);
    if (results.evening != null) worksheet.cell('E12').value(results.evening);
    if (results.night != null) worksheet.cell('E14').value(results.night);
    await saveExcelWorkbook(workbook);

    return NextResponse.json({
      success: true,
      parsed: results,
    });
  } catch (error: any) {
    console.error('Error processing shift:', error);
    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Failed to process shift images',
      },
      { status: 500 }
    );
  }
}

