declare module 'xlsx-populate' {
  interface Cell {
    value(): any;
    value(value: any): Cell;
  }

  interface Worksheet {
    name(): string;
    cell(address: string): Cell;
  }

  interface Workbook {
    sheet(nameOrIndex: string | number): Worksheet | null;
    sheets(): Worksheet[];
    toFileAsync(path: string): Promise<void>;
  }

  interface XlsxPopulate {
    fromFileAsync(path: string): Promise<Workbook>;
  }

  const XlsxPopulate: XlsxPopulate;
  export default XlsxPopulate;
}

