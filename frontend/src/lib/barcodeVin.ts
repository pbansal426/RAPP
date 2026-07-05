// VIN alphabet excludes I, O, Q (visually ambiguous with 1/0/9) — mirrors the
// pattern backend/routers/vin.py uses to sanitize OCR-extracted VIN text.
const VIN_PATTERN = /[A-HJ-NPR-Z0-9]{17}/;

// Door-jamb VIN barcodes (Code 39/128/93) sometimes wrap the 17-char VIN in
// delimiter characters (Code 39 uses "*" as a start/stop symbol) or extra
// label text — strip non-alphanumerics and pull out the VIN-shaped run
// rather than requiring the whole decoded string to be exactly the VIN.
export function extractVinFromBarcodeText(raw: string): string | null {
  const cleaned = raw.toUpperCase().replace(/[^A-Z0-9]/g, '');
  const match = cleaned.match(VIN_PATTERN);
  return match ? match[0] : null;
}
