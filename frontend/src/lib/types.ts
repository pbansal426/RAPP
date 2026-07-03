// Shared request/response shapes for the backend API. Mirrors the Pydantic
// models in backend/main.py — see the "Pinned contract" section in
// CLAUDE.md before changing any of these; presentational code may read new
// fields off these shapes but must not invent new ones.

/** One of the five powertrain categories the backend/UI reason about. */
export type Powertrain =
  | 'Gasoline'
  | 'Diesel'
  | 'Hybrid'
  | 'Plug-in Hybrid'
  | 'Electric (EV)';

/**
 * Vehicle identity, sent as the optional `vehicle` field on
 * /api/diagnose and /api/repair requests, and also the shape of a decoded
 * /api/vin/{vin} response and of `rapp_vin_data` in localStorage. Every
 * field is optional because /api/vin/{vin} only returns what NHTSA actually
 * has data for, and request payloads only ever need a subset.
 */
export interface VehicleInfo {
  year?: string | number | null;
  make?: string | null;
  model?: string | null;
  trim?: string | null;
  engine?: string | null;
  drive_type?: string | null;
  body_class?: string | null;
  vehicle_type?: string | null;
  fuel_type?: string | null;
  powertrain?: Powertrain | string | null;
}

export interface DiagnoseRequest {
  vin: string;
  symptoms: string;
  obd_codes: string[];
  tools: string[];
  vehicle?: VehicleInfo | null;
}

export interface RepairRequest extends DiagnoseRequest {
  stripe_session_id: string;
}

/** One purchasable option for a recommended part, at a specific tier. */
export interface PartOption {
  tier: 'OEM' | 'Aftermarket / Budget' | 'Upgrade';
  brand: string;
  part_number: string | null;
  title: string;
  estimated_price: number;
  purchase_url: string;
  rationale: string;
}

export interface RecommendedPart {
  part_name: string;
  options: PartOption[];
}

export interface CostBreakdown {
  /** [min, max] */
  dealership_cost_range: [number, number];
  /** [min, max] */
  independent_shop_range: [number, number];
  parts_total: number;
  /** RAPP guide fee ($4.00) + parts_total */
  diy_total: number;
  estimated_labor_hours: number;
}

export interface DiagnosisResponse {
  summary: string;
  is_high_risk: boolean;
  high_risk_system: string | null;
  warning_message: string | null;
  recommended_parts: RecommendedPart[];
  cost_breakdown: CostBreakdown | null;
}

export interface RepairResponse {
  repair_steps: string[];
  citations: string[];
}

/** GET /api/vin/{vin} response — a fully-decoded VehicleInfo, always with
 * year/make/model populated (the endpoint 404s otherwise). */
export type VinDecodeResponse = VehicleInfo & {
  year: string | number;
  make: string;
  model: string;
};

/** POST /api/vin/ocr response. `decoded_vehicle` is null if the VIN read
 * from the photo didn't decode against NHTSA (e.g. OCR misread a digit). */
export interface VinOcrResponse {
  vin: string;
  confidence: number;
  decoded_vehicle: VinDecodeResponse | null;
}
