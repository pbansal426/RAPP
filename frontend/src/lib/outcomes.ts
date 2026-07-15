'use client';

import { api } from './api';
import type { OutcomeCreateRequest, OutcomeResponse, OutcomeStatsResponse } from './types';

export async function submitOutcome(request: OutcomeCreateRequest): Promise<OutcomeResponse> {
  return api.post<OutcomeResponse>('/api/outcomes', request);
}

export async function getOutcomeStats(
  make: string,
  model: string,
  category?: string
): Promise<OutcomeStatsResponse> {
  const params = new URLSearchParams({ make, model });
  if (category) params.set('category', category);
  return api.get<OutcomeStatsResponse>(`/api/outcomes/stats?${params.toString()}`);
}
