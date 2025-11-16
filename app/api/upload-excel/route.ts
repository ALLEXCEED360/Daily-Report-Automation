import { NextRequest, NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get('file') as File;

    if (!file) {
      return NextResponse.json(
        { error: 'No file provided' },
        { status: 400 }
      );
    }

    // Validate file type
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      return NextResponse.json(
        { error: 'File must be an Excel file (.xlsx or .xls)' },
        { status: 400 }
      );
    }

    // Read the file buffer
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    // Define the path to save the file
    const excelPath = path.join(process.cwd(), 'public', 'daily_report_template.xlsx');

    // Write the file to the public folder (this will replace the existing file)
    await fs.writeFile(excelPath, buffer);

    return NextResponse.json({
      success: true,
      message: 'Excel file uploaded and replaced successfully',
      filename: file.name,
    });
  } catch (error: any) {
    console.error('Error uploading Excel file:', error);
    return NextResponse.json(
      { error: 'Failed to upload Excel file', details: error.message },
      { status: 500 }
    );
  }
}

