// Mirrors backend/routers/vin.py's _vin_check_digit_valid — used client-side
// to flag likely-wrong OCR reads (e.g. from the free Tesseract fallback)
// before the VIN ever reaches the backend.
const VIN_TRANSLITERATION: Record<string, number> = {
  '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
  A: 1, B: 2, C: 3, D: 4, E: 5, F: 6, G: 7, H: 8,
  J: 1, K: 2, L: 3, M: 4, N: 5, P: 7, R: 9,
  S: 2, T: 3, U: 4, V: 5, W: 6, X: 7, Y: 8, Z: 9,
};
const VIN_POSITION_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2];

export function isValidVinCheckDigit(vin: string): boolean {
  if (vin.length !== 17) return false;
  let total = 0;
  for (let i = 0; i < 17; i++) {
    const value = VIN_TRANSLITERATION[vin[i]];
    if (value === undefined) return false;
    total += value * VIN_POSITION_WEIGHTS[i];
  }
  const remainder = total % 11;
  const expected = remainder === 10 ? 'X' : String(remainder);
  return vin[8] === expected;
}
