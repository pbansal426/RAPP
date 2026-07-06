'use client';

import { api } from './api';
import type { ComplaintsSummaryResponse, RecallsResponse } from './types';

function vehicleQuery(year: string | number, make: string, model: string): string {
  return new URLSearchParams({ year: String(year), make, model }).toString();
}

export async function getOpenRecalls(
  year: string | number,
  make: string,
  model: string
): Promise<RecallsResponse> {
  return api.get<RecallsResponse>(`/api/vehicle-safety/recalls?${vehicleQuery(year, make, model)}`);
}

export async function getComplaintsSummary(
  year: string | number,
  make: string,
  model: string
): Promise<ComplaintsSummaryResponse> {
  return api.get<ComplaintsSummaryResponse>(
    `/api/vehicle-safety/complaints-summary?${vehicleQuery(year, make, model)}`
  );
}
