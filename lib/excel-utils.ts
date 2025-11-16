import XlsxPopulate from 'xlsx-populate';
import path from 'path';
import { promises as fs } from 'fs';

export async function loadExcelWorkbook(dayNumber: number) {
  const excelPath = path.join(process.cwd(), 'public', 'daily_report_template.xlsx');
  const workbook = await XlsxPopulate.fromFileAsync(excelPath);
  
  // Select sheet by day number
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
    throw new Error(`Sheet for day ${dayNumber} not found. Available sheets: ${availableSheets}`);
  }
  
  return { workbook, worksheet, sheetName };
}

export async function saveExcelWorkbook(workbook: any) {
  const excelPath = path.join(process.cwd(), 'public', 'daily_report_template.xlsx');
  await workbook.toFileAsync(excelPath);
}

export function toNum(x: any): number {
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

export function toFloat(s: string | null | undefined): number | null {
  if (!s) {
    return null;
  }
  s = String(s).replace(/\$/g, '').replace(/\s/g, '').replace(/\u200b/g, '');
  s = s.replace(/-$/, '');
  s = s.replace(/,/g, '');
  try {
    return parseFloat(s);
  } catch {
    return null;
  }
}

export function parseJSONFromText(text: string): any | null {
  if (!text) {
    return null;
  }
  const match = text.match(/\{[\s\S]*\}/);
  if (match) {
    try {
      return JSON.parse(match[0]);
    } catch {
      return null;
    }
  }
  return null;
}

