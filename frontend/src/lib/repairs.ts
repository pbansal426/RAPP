'use client';

import { api } from './api';

export interface SavedRepairInput {
  vin: string;
  year?: string;
  make?: string;
  model?: string;
  engine?: string;
  powertrain?: string;
  symptoms: string;
  // Reference to the checkout session that unlocked this repair. We never
  // store card data ourselves — this lets future checkouts prefill/reuse
  // the customer's payment method via the processor.
  paymentSessionId?: string;
  // The citations returned by /api/repair at the time this guide was
  // unlocked/saved. Captured at save time rather than re-derived later,
  // since a re-fetch of /api/repair could return different citations for
  // the same vehicle/symptoms after new TSB ingestion.
  citations?: string[];
}

export interface SavedRepair extends SavedRepairInput {
  id: string;
  savedAt: string | null;
}

interface SavedRepairResponse {
  id: string;
  vin: string;
  year: string | null;
  make: string | null;
  model: string | null;
  engine: string | null;
  powertrain: string | null;
  symptoms: string;
  payment_session_id: string | null;
  citations: string[] | null;
  saved_at: string | null;
}

function toSavedRepair(r: SavedRepairResponse): SavedRepair {
  return {
    id: r.id,
    vin: r.vin,
    year: r.year ?? undefined,
    make: r.make ?? undefined,
    model: r.model ?? undefined,
    engine: r.engine ?? undefined,
    powertrain: r.powertrain ?? undefined,
    symptoms: r.symptoms,
    paymentSessionId: r.payment_session_id ?? undefined,
    citations: r.citations ?? undefined,
    savedAt: r.saved_at ? new Date(r.saved_at).toLocaleDateString() : null,
  };
}

// The backend derives identity from the bearer token attached by api.ts, so
// callers no longer need to pass a uid explicitly.
export async function saveRepair(repair: SavedRepairInput): Promise<void> {
  await api.post<SavedRepairResponse>('/api/repairs', {
    vin: repair.vin,
    year: repair.year ?? null,
    make: repair.make ?? null,
    model: repair.model ?? null,
    engine: repair.engine ?? null,
    powertrain: repair.powertrain ?? null,
    symptoms: repair.symptoms,
    payment_session_id: repair.paymentSessionId ?? null,
    citations: repair.citations ?? null,
  });
}

export async function listRepairs(): Promise<SavedRepair[]> {
  const repairs = await api.get<SavedRepairResponse[]>('/api/repairs');
  return repairs.map(toSavedRepair);
}
