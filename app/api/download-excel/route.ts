import { NextRequest, NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

export async function GET(request: NextRequest) {
  try {
    const excelPath = path.join(process.cwd(), 'public', 'daily_report_template.xlsx');
    
    // Check if file exists
    try {
      await fs.access(excelPath);
    } catch {
      return NextResponse.json(
        { error: 'Excel file not found' },
        { status: 404 }
      );
    }

    // Read the file
    const fileBuffer = await fs.readFile(excelPath);

    // Return the file with appropriate headers
    return new NextResponse(fileBuffer, {
      headers: {
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'Content-Disposition': `attachment; filename="daily_report_template.xlsx"`,
      },
    });
  } catch (error: any) {
    console.error('Error serving Excel file:', error);
    return NextResponse.json(
      { error: 'Failed to serve Excel file' },
      { status: 500 }
    );
  }
}

