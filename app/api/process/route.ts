import { NextRequest, NextResponse } from 'next/server';
import { GoogleGenerativeAI } from '@google/generative-ai';
import { loadExcelWorkbook, saveExcelWorkbook, toNum, toFloat, parseJSONFromText } from '@/lib/excel-utils';

function parseCurrencyLike(text: string): number | null {
  if (!text) return null;
  const txt = text.replace(/\n/g, ' ').replace(/\r/g, ' ');
  
  let match = txt.match(/EBT[^0-9\.\-]*([\$\-]?\s*\d{1,3}(?:[,]\d{3})*(?:\.\d{1,2})?)/i);
  if (match) return toFloat(match[1]);
  
  match = txt.match(/EBT(.{0,60}?)([\$\-]?\s*\d{1,3}(?:[,]\d{3})*(?:\.\d{1,2})?)/i);
  if (match) return toFloat(match[2]);
  
  match = txt.match(/(?:EBT.*?TOTAL|TOTAL.*?EBT)(.{0,60}?)([\$\-]?\s*\d{1,3}(?:[,]\d{3})*(?:\.\d{1,2})?)/i);
  if (match) return toFloat(match[2]);
  
  match = txt.match(/([\$\-]?\s*\d{1,3}(?:[,]\d{3})*(?:\.\d{1,2})?)/);
  if (match) return toFloat(match[1]);
  
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
    const file = formData.get('image') as File;
    const processorType = formData.get('processorType') as string;
    const dayNumberStr = formData.get('dayNumber') as string;

    if (!file) {
      return NextResponse.json(
        { error: 'No image file provided' },
        { status: 400 }
      );
    }

    if (!processorType) {
      return NextResponse.json(
        { error: 'Processor type is required' },
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

    // Process based on processor type
    let prompt = '';
    let result: any = {};

    switch (processorType) {
      case 'batch':
        prompt = `Please analyze this Batch Report image and return the dollar amount that corresponds to the EBT total.
Look for lines containing the word 'EBT' (or 'E B T') and a dollar amount or the word 'Total' near EBT.
Return a short line such as: EBT: 123.45
If you cannot find an EBT amount, return NOT_FOUND.`;
        const batchResult = await model.generateContent([prompt, { inlineData: { data: base64Image, mimeType } }]);
        const batchText = batchResult.response.text();
        const extractedValue = parseCurrencyLike(batchText);
        if (extractedValue === null) {
          return NextResponse.json({ success: false, error: 'EBT not found', raw: batchText });
        }
        const { workbook, worksheet } = await loadExcelWorkbook(dayNumber);
        const z10Cell = worksheet.cell('Z10');
        z10Cell.value(extractedValue);
        await saveExcelWorkbook(workbook);
        return NextResponse.json({
          success: true,
          extracted_ebt: extractedValue,
          raw: batchText,
        });

      case 'day1':
        prompt = `Please analyze the Day_Report1 image and extract the following values:
1. Net sales total (labelled like 'Net Sales Total', 'Total Net Sales', or similar)
2. Credit amount from cashier details (exclude MOP sales)
3. Debit amount from cashier details (exclude MOP sales)
Respond with a JSON object like: {"net_sales_total": 1234.56, "credit": 567.89, "debit": 123.45}`;
        const day1Result = await model.generateContent([prompt, { inlineData: { data: base64Image, mimeType } }]);
        const day1Text = day1Result.response.text();
        const day1Parsed = parseJSONFromText(day1Text);
        if (!day1Parsed) {
          return NextResponse.json({ success: false, error: 'Could not parse values', raw: day1Text });
        }
        const { workbook: wb1, worksheet: ws1 } = await loadExcelWorkbook(dayNumber);
        if (day1Parsed.net_sales_total != null) ws1.cell('L7').value(day1Parsed.net_sales_total);
        if (day1Parsed.credit != null) ws1.cell('I12').value(day1Parsed.credit);
        if (day1Parsed.debit != null) ws1.cell('I13').value(day1Parsed.debit);
        await saveExcelWorkbook(wb1);
        return NextResponse.json({ success: true, parsed: day1Parsed, raw: day1Text });

      case 'day2':
        prompt = `Please analyze this Day Report page image and extract values from the Category Report section and the Tax Report section.
From the Category Report (look for labels like 'LOTTERY', 'Lottery', 'lottery'): Return the net sales value for LOTTERY.
From the Category Report (look for labels like 'Fuel deposit', 'fuel deposit', 'Fuel Deposit'): Return the fuel deposit net sales value.
From the Tax Report section: Return the TAXABLE-SALES value and the TAXES value.
Return a JSON object like: {"lottery_net": 38.50, "fuel_deposit": 1234.56, "taxable_sales": 9876.54, "taxes": 123.45}`;
        const day2Result = await model.generateContent([prompt, { inlineData: { data: base64Image, mimeType } }]);
        const day2Text = day2Result.response.text();
        const day2Parsed = parseJSONFromText(day2Text);
        if (!day2Parsed) {
          return NextResponse.json({ success: false, error: 'Could not parse values', raw: day2Text });
        }
        const { workbook: wb2, worksheet: ws2 } = await loadExcelWorkbook(dayNumber);
        if (day2Parsed.lottery_net != null) ws2.cell('L6').value(day2Parsed.lottery_net);
        if (day2Parsed.fuel_deposit != null) ws2.cell('F15').value(day2Parsed.fuel_deposit);
        if (day2Parsed.taxable_sales != null) ws2.cell('F16').value(day2Parsed.taxable_sales);
        if (day2Parsed.taxes != null) {
          ws2.cell('F17').value(day2Parsed.taxes);
          ws2.cell('Z11').value(day2Parsed.taxes);
        }
        await saveExcelWorkbook(wb2);
        return NextResponse.json({ success: true, parsed: day2Parsed, raw: day2Text });

      case 'day3':
        prompt = `Please analyze this Day Report page image (FP/HOSE RUNNING RPT) and extract the PRODUCT TOTALS volumes for: UNLEADED, PLUS, PREMIUM, DIESEL.
Return a JSON object with keys exactly: {"unleaded": 1234.56, "plus": 234.56, "premium": 345.67, "diesel": 456.78}`;
        const day3Result = await model.generateContent([prompt, { inlineData: { data: base64Image, mimeType } }]);
        const day3Text = day3Result.response.text();
        const day3Parsed = parseJSONFromText(day3Text);
        if (!day3Parsed) {
          return NextResponse.json({ success: false, error: 'Could not parse values', raw: day3Text });
        }
        const { workbook: wb3, worksheet: ws3 } = await loadExcelWorkbook(dayNumber);
        if (day3Parsed.unleaded != null) ws3.cell('F26').value(day3Parsed.unleaded);
        if (day3Parsed.plus != null) ws3.cell('H26').value(day3Parsed.plus);
        if (day3Parsed.premium != null) ws3.cell('G26').value(day3Parsed.premium);
        if (day3Parsed.diesel != null) ws3.cell('E26').value(day3Parsed.diesel);
        await saveExcelWorkbook(wb3);
        return NextResponse.json({ success: true, parsed: day3Parsed, raw: day3Text });

      case 'handwritten':
        prompt = `You will be given an image of a handwritten daily report. Extract the following values:
- Morning customers/count (labelled 'Morning' or 'Morning Shift') - can be decimal
- Evening customers/count (labelled 'Evening' or 'Evening Shift') - can be decimal
- Night customers/count (labelled 'Night' or 'Night Shift') - can be decimal
- Total Cash (labelled 'Total Cash', 'Total Cash:' or similar)
- Any numeric values listed under a section/label 'Additional' — return the sum of those numbers.
- Game in and Game out values
Return a JSON object exactly like: {"morning": 358.75, "evening": 456.50, "night": 78.25, "total_cash": 1234.56, "additional_sum": 45.67, "game_in": 12.34, "game_out": 56.78}`;
        const hwResult = await model.generateContent([prompt, { inlineData: { data: base64Image, mimeType } }]);
        const hwText = hwResult.response.text();
        const hwParsed = parseJSONFromText(hwText);
        if (!hwParsed) {
          return NextResponse.json({ success: false, error: 'Could not parse values', raw: hwText });
        }
        const { workbook: wbHw, worksheet: wsHw } = await loadExcelWorkbook(dayNumber);
        if (hwParsed.morning != null) wsHw.cell('D9').value(hwParsed.morning);
        if (hwParsed.evening != null) wsHw.cell('D11').value(hwParsed.evening);
        if (hwParsed.night != null) wsHw.cell('D13').value(hwParsed.night);
        if (hwParsed.total_cash != null) wsHw.cell('L14').value(hwParsed.total_cash);
        if (hwParsed.additional_sum != null) wsHw.cell('Z17').value(hwParsed.additional_sum);
        if (hwParsed.game_in != null) wsHw.cell('F34').value(hwParsed.game_in);
        if (hwParsed.game_out != null) wsHw.cell('F35').value(hwParsed.game_out);
        await saveExcelWorkbook(wbHw);
        return NextResponse.json({ success: true, parsed: hwParsed, raw: hwText });

      case 'lotto':
        prompt = `Please analyze this Lotto Machine Report image and extract the following specific values:
1. Look for "DRW GM NET SALES" (or "DRAW GM NET SALES") and get the dollar amount after it
2. Look for "DRW GM CASHES" (or "DRAW GM CASHES") and get the dollar amount after it
3. Look for "SCRATCH CASHES" and get the dollar amount after it
Respond with a JSON object like: {"drw_gm_net_sales": 38.50, "drw_gm_cashes": 2.00, "scratch_cashes": 122.00}`;
        const lottoResult = await model.generateContent([prompt, { inlineData: { data: base64Image, mimeType } }]);
        const lottoText = lottoResult.response.text();
        const lottoParsed = parseJSONFromText(lottoText);
        if (!lottoParsed) {
          return NextResponse.json({ success: false, error: 'Could not parse values', raw: lottoText });
        }
        const { workbook: wbLotto, worksheet: wsLotto } = await loadExcelWorkbook(dayNumber);
        if (lottoParsed.drw_gm_net_sales != null) wsLotto.cell('T30').value(lottoParsed.drw_gm_net_sales);
        const totalCashes = (lottoParsed.drw_gm_cashes || 0) + (lottoParsed.scratch_cashes || 0);
        if (totalCashes > 0) wsLotto.cell('Z9').value(totalCashes);
        await saveExcelWorkbook(wbLotto);
        return NextResponse.json({ success: true, parsed: lottoParsed, raw: lottoText });

      case 'handwritten_lotto_end':
        // Process first image (required) - maps to I26:AB26
        prompt = `Read this Handwritten Report image. Locate the 'Daily Lotto' section and the 'End no' column (or similar). Return the End no values top-to-bottom as a JSON array. If not found, return NOT_FOUND. Respond with JSON like: {"end_values": [123,124,...] }`;
        const hwLottoResult = await model.generateContent([prompt, { inlineData: { data: base64Image, mimeType } }]);
        const hwLottoText = hwLottoResult.response.text();
        let hwLottoParsed = parseJSONFromText(hwLottoText);
        
        let values1: (number | null)[] = [];
        if (hwLottoParsed && hwLottoParsed.end_values && Array.isArray(hwLottoParsed.end_values)) {
          values1 = hwLottoParsed.end_values.slice(0, 20);
        }
        while (values1.length < 20) {
          values1.push(null);
        }

        // Process second image (optional) - maps to I33:X33
        const secondFile = formData.get('image2') as File;
        let values2: (number | null)[] | null = null;
        let hwLotto2Text = '';

        if (secondFile) {
          const secondBytes = await secondFile.arrayBuffer();
          const secondBuffer = Buffer.from(secondBytes);
          const secondBase64 = secondBuffer.toString('base64');
          const secondMime = secondFile.type || 'image/jpeg';
          const hwLotto2Result = await model.generateContent([prompt, { inlineData: { data: secondBase64, mimeType: secondMime } }]);
          hwLotto2Text = hwLotto2Result.response.text();
          const hwLotto2Parsed = parseJSONFromText(hwLotto2Text);
          
          // Initialize with 16 null values
          values2 = Array(16).fill(null);
          
          if (hwLotto2Parsed && hwLotto2Parsed.end_values && Array.isArray(hwLotto2Parsed.end_values)) {
            // Copy extracted values (up to 16) into the array
            for (let i = 0; i < Math.min(hwLotto2Parsed.end_values.length, 16); i++) {
              values2[i] = hwLotto2Parsed.end_values[i];
            }
          }
        }

        // Write to Excel
        const { workbook: wbHwLotto, worksheet: wsHwLotto } = await loadExcelWorkbook(dayNumber);
        
        // Write first set of values to I26:AB26 (20 values)
        const colLetters26 = ['I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','AA','AB'];
        for (let i = 0; i < colLetters26.length; i++) {
          const val = values1[i];
          if (val != null) {
            wsHwLotto.cell(`${colLetters26[i]}26`).value(val);
          }
        }
        
        // Write second set of values to I33:X33 (16 values) - iterate through all 16 columns
        if (values2) {
          const colLetters33 = ['I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X'];
          for (let i = 0; i < colLetters33.length; i++) {
            const val = values2[i];
            if (val != null) {
              wsHwLotto.cell(`${colLetters33[i]}33`).value(val);
            }
          }
        }
        
        await saveExcelWorkbook(wbHwLotto);
        return NextResponse.json({ 
          success: true, 
          parsed: { 
            report1_values: values1,
            report2_values: values2,
          }, 
          raw: hwLottoText,
          raw2: hwLotto2Text || undefined,
        });

      default:
        return NextResponse.json(
          { error: `Unknown processor type: ${processorType}` },
          { status: 400 }
        );
    }
  } catch (error: any) {
    console.error('Error processing:', error);
    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Failed to process image',
      },
      { status: 500 }
    );
  }
}

