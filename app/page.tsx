'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Spinner } from '@/components/ui/spinner';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Download } from 'lucide-react';

interface ProcessResult {
  success: boolean;
  extracted_ebt?: number;
  parsed?: any;
  raw?: string;
  error?: string;
}

export default function Home() {
  const [dayNumber, setDayNumber] = useState<string>('');
  const [activeTab, setActiveTab] = useState<string>('batch');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Record<string, ProcessResult | null>>({});
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleDownload = async () => {
    try {
      const response = await fetch('/api/download-excel');
      if (!response.ok) throw new Error('Failed to download file');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'daily_report_template.xlsx';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error: any) {
      alert('Failed to download Excel file. Please try again.');
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      setUploadMessage({ type: 'error', text: 'Please upload an Excel file (.xlsx or .xls)' });
      e.target.value = ''; // Reset input
      return;
    }

    setUploading(true);
    setUploadMessage(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/upload-excel', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to upload file');
      }

      setUploadMessage({ type: 'success', text: `Successfully uploaded and replaced: ${data.filename}` });
      e.target.value = ''; // Reset input
      
      // Clear success message after 5 seconds
      setTimeout(() => setUploadMessage(null), 5000);
    } catch (error: any) {
      setUploadMessage({ type: 'error', text: error.message || 'Failed to upload Excel file' });
      e.target.value = ''; // Reset input
    } finally {
      setUploading(false);
    }
  };

  const processImage = async (processorType: string, file: File, file2?: File) => {
    if (!dayNumber) {
      alert('Please enter a day number (1-31)');
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('image', file);
      if (file2) {
        formData.append('image2', file2);
      }
      formData.append('processorType', processorType);
      formData.append('dayNumber', dayNumber);

      const response = await fetch('/api/process', {
        method: 'POST',
        body: formData,
      });

      const data: ProcessResult = await response.json();
      setResults(prev => ({ ...prev, [processorType]: data }));
    } catch (error: any) {
      setResults(prev => ({
        ...prev,
        [processorType]: { success: false, error: error.message || 'Failed to process image' },
      }));
    } finally {
      setLoading(false);
    }
  };

  const processShift = async (morningFile: File | null, eveningFile: File | null, nightFile: File | null) => {
    if (!dayNumber) {
      alert('Please enter a day number (1-31)');
      return;
    }

    if (!morningFile && !eveningFile && !nightFile) {
      alert('Please upload at least one shift image');
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      if (morningFile) formData.append('morning', morningFile);
      if (eveningFile) formData.append('evening', eveningFile);
      if (nightFile) formData.append('night', nightFile);
      formData.append('dayNumber', dayNumber);

      const response = await fetch('/api/process-shift', {
        method: 'POST',
        body: formData,
      });

      const data: ProcessResult = await response.json();
      setResults(prev => ({ ...prev, shift: data }));
    } catch (error: any) {
      setResults(prev => ({
        ...prev,
        shift: { success: false, error: error.message || 'Failed to process shift images' },
      }));
    } finally {
      setLoading(false);
    }
  };

  const ProcessorTab = ({ 
    id, 
    title, 
    description, 
    children 
  }: { 
    id: string; 
    title: string; 
    description: string; 
    children: React.ReactNode;
  }) => (
    <TabsContent value={id} className="mt-4">
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>{children}</CardContent>
      </Card>
    </TabsContent>
  );

  const ImageUploadSection = ({ 
    processorType, 
    label,
    allowSecondImage = false,
    secondLabel = 'Second Image (Optional)'
  }: { 
    processorType: string; 
    label: string;
    allowSecondImage?: boolean;
    secondLabel?: string;
  }) => {
    const [file, setFile] = useState<File | null>(null);
    const [file2, setFile2] = useState<File | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [preview2, setPreview2] = useState<string | null>(null);
    const result = results[processorType];

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFile = e.target.files?.[0];
      if (selectedFile) {
        setFile(selectedFile);
        const reader = new FileReader();
        reader.onloadend = () => setPreview(reader.result as string);
        reader.readAsDataURL(selectedFile);
      }
    };

    const handleFile2Change = (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFile = e.target.files?.[0];
      if (selectedFile) {
        setFile2(selectedFile);
        const reader = new FileReader();
        reader.onloadend = () => setPreview2(reader.result as string);
        reader.readAsDataURL(selectedFile);
      }
    };

    return (
      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor={`file-${processorType}`}>{label}</Label>
          <Input
            id={`file-${processorType}`}
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            disabled={loading}
            className="cursor-pointer"
            required
          />
        </div>

        {preview && (
          <div className="border rounded-lg overflow-hidden bg-zinc-100 dark:bg-zinc-900">
            <img src={preview} alt="Preview" className="w-full h-auto max-h-96 object-contain" />
          </div>
        )}

        {allowSecondImage && (
          <>
            <div className="space-y-2">
              <Label htmlFor={`file2-${processorType}`}>{secondLabel}</Label>
              <Input
                id={`file2-${processorType}`}
                type="file"
                accept="image/*"
                onChange={handleFile2Change}
                disabled={loading}
                className="cursor-pointer"
              />
            </div>

            {preview2 && (
              <div className="border rounded-lg overflow-hidden bg-zinc-100 dark:bg-zinc-900">
                <img src={preview2} alt="Preview 2" className="w-full h-auto max-h-96 object-contain" />
              </div>
            )}
          </>
        )}

        <Button
          onClick={() => file && processImage(processorType, file, file2 || undefined)}
          disabled={!file || !dayNumber || loading}
          className="w-full"
        >
          {loading ? (
            <>
              <Spinner className="mr-2" />
              Processing...
            </>
          ) : (
            'Process & Save to Excel'
          )}
        </Button>

        {result && (
          <div className="mt-4 p-4 rounded-lg border">
            {result.success ? (
              <div className="text-green-600 dark:text-green-400">
                <p className="font-semibold mb-2">✓ Successfully processed and saved!</p>
                {result.parsed && (
                  <div className="mt-2 space-y-2">
                    {result.parsed.report1_values && (
                      <div>
                        <p className="text-sm font-medium">Report 1 Values (I26:AB26):</p>
                        <p className="text-xs">{result.parsed.report1_values.filter((v: any) => v != null).length} values extracted</p>
                      </div>
                    )}
                    {result.parsed.report2_values && (
                      <div>
                        <p className="text-sm font-medium">Report 2 Values (I33:X33):</p>
                        <p className="text-xs">{result.parsed.report2_values.filter((v: any) => v != null).length} values extracted</p>
                      </div>
                    )}
                    <details className="mt-2">
                      <summary className="text-sm cursor-pointer">View All Values</summary>
                      <pre className="text-xs mt-2 bg-zinc-50 dark:bg-zinc-900 p-2 rounded overflow-auto">
                        {JSON.stringify(result.parsed, null, 2)}
                      </pre>
                    </details>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-red-600 dark:text-red-400">
                <p className="font-semibold">✗ Error: {result.error}</p>
              </div>
            )}
            {result.raw && (
              <details className="mt-2">
                <summary className="text-sm cursor-pointer">Raw Response</summary>
                <pre className="text-xs mt-2 bg-zinc-50 dark:bg-zinc-900 p-2 rounded overflow-auto">
                  {result.raw}
                </pre>
              </details>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 font-sans dark:bg-black p-4">
      <main className="w-full max-w-6xl">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-black dark:text-zinc-50 mb-2">
            Daily Report Automation
          </h1>
          <p className="text-lg text-zinc-600 dark:text-zinc-400">
            Process various report images and extract data to Excel
          </p>
        </div>

        <Card className="mb-4">
          <CardContent className="pt-6">
            <div className="space-y-2">
              <Label htmlFor="dayNumber">Day Number (1-31)</Label>
              <Input
                id="dayNumber"
                type="number"
                min="1"
                max="31"
                value={dayNumber}
                onChange={(e) => setDayNumber(e.target.value)}
                placeholder="Enter day number (1-31)"
                required
              />
              <p className="text-sm text-zinc-500 dark:text-zinc-400">
                The day number corresponds to the sheet number in the Excel file
              </p>
            </div>
          </CardContent>
        </Card>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4 lg:grid-cols-8">
            <TabsTrigger value="batch">Batch</TabsTrigger>
            <TabsTrigger value="day1">Day 1</TabsTrigger>
            <TabsTrigger value="day2">Day 2</TabsTrigger>
            <TabsTrigger value="day3">Day 3</TabsTrigger>
            <TabsTrigger value="handwritten">Handwritten</TabsTrigger>
            <TabsTrigger value="lotto">Lotto</TabsTrigger>
            <TabsTrigger value="shift">Shift</TabsTrigger>
            <TabsTrigger value="handwritten_lotto_end">Lotto End</TabsTrigger>
          </TabsList>

          <ProcessorTab
            id="batch"
            title="Batch Report Processor"
            description="Extract EBT total from batch report image"
          >
            <ImageUploadSection processorType="batch" label="Batch Report Image" />
          </ProcessorTab>

          <ProcessorTab
            id="day1"
            title="Day 1 Report Processor"
            description="Extract Net Sales Total, Credit, and Debit from Day Report 1"
          >
            <ImageUploadSection processorType="day1" label="Day Report 1 Image" />
          </ProcessorTab>

          <ProcessorTab
            id="day2"
            title="Day 2 Report Processor"
            description="Extract Lottery Net, Fuel Deposit, Taxable Sales, and Taxes from Day Report 2"
          >
            <ImageUploadSection processorType="day2" label="Day Report 2 Image" />
          </ProcessorTab>

          <ProcessorTab
            id="day3"
            title="Day 3 Report Processor"
            description="Extract product volumes (Unleaded, Plus, Premium, Diesel) from FP/Hose Running Report"
          >
            <ImageUploadSection processorType="day3" label="FP/Hose Running Report Image" />
          </ProcessorTab>

          <ProcessorTab
            id="handwritten"
            title="Handwritten Report Processor"
            description="Extract Morning/Evening/Night counts, Total Cash, Additional sum, and Game in/out values"
          >
            <ImageUploadSection processorType="handwritten" label="Handwritten Report Image" />
          </ProcessorTab>

          <ProcessorTab
            id="lotto"
            title="Lotto Machine Report Processor"
            description="Extract DRW GM Net Sales, DRW GM Cashes, and Scratch Cashes from Lotto Machine Report"
          >
            <ImageUploadSection processorType="lotto" label="Lotto Machine Report Image" />
          </ProcessorTab>

          <ProcessorTab
            id="shift"
            title="Shift Report Processor"
            description="Extract customer counts from Morning, Evening, and Night shift reports"
          >
            <ShiftProcessorSection 
              onProcess={processShift} 
              loading={loading} 
              dayNumber={dayNumber}
              result={results.shift}
            />
          </ProcessorTab>

          <ProcessorTab
            id="handwritten_lotto_end"
            title="Handwritten Lotto End Processor"
            description="Extract End no values from handwritten report (Daily Lotto section). First image maps to I26:AB26, optional second image maps to I33:X33"
          >
            <ImageUploadSection 
              processorType="handwritten_lotto_end" 
              label="Handwritten Report Image (Required)" 
              allowSecondImage={true}
              secondLabel="Handwritten Report 2 Image (Optional - maps to I33:X33)"
            />
          </ProcessorTab>
        </Tabs>

        <Card className="mt-4">
          <CardContent className="pt-6 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="excel-upload">Upload Updated Excel Template</Label>
              <div className="flex gap-2">
                <Input
                  id="excel-upload"
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleFileUpload}
                  disabled={uploading}
                  className="cursor-pointer"
                />
                {uploading && <Spinner className="self-center" />}
              </div>
              {uploadMessage && (
                <div className={`text-sm p-2 rounded ${
                  uploadMessage.type === 'success' 
                    ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400' 
                    : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400'
                }`}>
                  {uploadMessage.text}
                </div>
              )}
              <p className="text-sm text-zinc-500 dark:text-zinc-400">
                Upload a new Excel file to replace the current template in the public folder
              </p>
            </div>
            <Button onClick={handleDownload} className="w-full" variant="outline">
              <Download className="mr-2 size-4" />
              Download Updated Excel File
            </Button>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

function ShiftProcessorSection({ 
  onProcess, 
  loading, 
  dayNumber,
  result
}: { 
  onProcess: (morning: File | null, evening: File | null, night: File | null) => void;
  loading: boolean;
  dayNumber: string;
  result?: ProcessResult | null;
}) {
  const [morningFile, setMorningFile] = useState<File | null>(null);
  const [eveningFile, setEveningFile] = useState<File | null>(null);
  const [nightFile, setNightFile] = useState<File | null>(null);
  const [previews, setPreviews] = useState<Record<string, string | null>>({});

  const handleFileChange = (type: 'morning' | 'evening' | 'night', e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (type === 'morning') setMorningFile(file);
      if (type === 'evening') setEveningFile(file);
      if (type === 'night') setNightFile(file);
      
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviews(prev => ({ ...prev, [type]: reader.result as string }));
      };
      reader.readAsDataURL(file);
    }
  };

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label>Morning Shift Image</Label>
        <Input
          type="file"
          accept="image/*"
          onChange={(e) => handleFileChange('morning', e)}
          disabled={loading}
        />
        {previews.morning && (
          <img src={previews.morning} alt="Morning preview" className="mt-2 max-h-48 object-contain border rounded" />
        )}
      </div>

      <div className="space-y-2">
        <Label>Evening Shift Image</Label>
        <Input
          type="file"
          accept="image/*"
          onChange={(e) => handleFileChange('evening', e)}
          disabled={loading}
        />
        {previews.evening && (
          <img src={previews.evening} alt="Evening preview" className="mt-2 max-h-48 object-contain border rounded" />
        )}
      </div>

      <div className="space-y-2">
        <Label>Night Shift Image</Label>
        <Input
          type="file"
          accept="image/*"
          onChange={(e) => handleFileChange('night', e)}
          disabled={loading}
        />
        {previews.night && (
          <img src={previews.night} alt="Night preview" className="mt-2 max-h-48 object-contain border rounded" />
        )}
      </div>

      <Button
        onClick={() => onProcess(morningFile, eveningFile, nightFile)}
        disabled={(!morningFile && !eveningFile && !nightFile) || !dayNumber || loading}
        className="w-full"
      >
        {loading ? (
          <>
            <Spinner className="mr-2" />
            Processing...
          </>
        ) : (
          'Process & Save to Excel'
        )}
      </Button>

      {result && (
        <div className="mt-4 p-4 rounded-lg border">
          {result.success ? (
            <div className="text-green-600 dark:text-green-400">
              <p className="font-semibold mb-2">✓ Successfully processed and saved!</p>
              {result.parsed && (
                <div className="mt-2 space-y-1">
                  {result.parsed.morning != null && <p>Morning: {result.parsed.morning}</p>}
                  {result.parsed.evening != null && <p>Evening: {result.parsed.evening}</p>}
                  {result.parsed.night != null && <p>Night: {result.parsed.night}</p>}
                </div>
              )}
            </div>
          ) : (
            <div className="text-red-600 dark:text-red-400">
              <p className="font-semibold">✗ Error: {result.error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
