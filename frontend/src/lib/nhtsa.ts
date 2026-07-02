const VPIC = 'https://vpic.nhtsa.dot.gov/api/vehicles';

// NHTSA splits consumer vehicles across three vehicle types: sedans/coupes are
// "passenger car", SUVs/minivans are "MPV", pickups are "truck". All three must
// be merged to cover a make's full lineup.
const VEHICLE_TYPES = ['passenger car', 'multipurpose passenger vehicle (mpv)', 'truck'];

// Shown first in the make dropdown; everything else follows alphabetically.
const POPULAR_MAKES = [
  'TOYOTA', 'HONDA', 'FORD', 'CHEVROLET', 'NISSAN', 'JEEP', 'HYUNDAI', 'KIA',
  'SUBARU', 'RAM', 'GMC', 'MAZDA', 'VOLKSWAGEN', 'BMW', 'MERCEDES-BENZ',
  'LEXUS', 'AUDI', 'TESLA', 'DODGE', 'ACURA', 'CADILLAC', 'CHRYSLER',
  'BUICK', 'INFINITI', 'LINCOLN', 'VOLVO', 'MITSUBISHI', 'PORSCHE', 'MINI',
];

interface VpicResponse<T> {
  Count: number;
  Results: T[];
}

async function vpicGet<T>(path: string): Promise<T[]> {
  const res = await fetch(`${VPIC}/${path}?format=json`);
  if (!res.ok) throw new Error(`NHTSA API error (${res.status})`);
  const data = (await res.json()) as VpicResponse<T>;
  return data.Results ?? [];
}

export interface MakeGroups {
  popular: string[];
  other: string[];
}

let makesCache: MakeGroups | null = null;

export async function fetchAllMakes(): Promise<MakeGroups> {
  if (makesCache) return makesCache;

  const cached = sessionStorage.getItem('rapp_nhtsa_makes');
  if (cached) {
    makesCache = JSON.parse(cached) as MakeGroups;
    return makesCache;
  }

  const results = await Promise.all(
    VEHICLE_TYPES.map((vt) =>
      vpicGet<{ MakeName: string }>(`GetMakesForVehicleType/${encodeURIComponent(vt)}`)
    )
  );
  const all = new Set<string>();
  for (const list of results) {
    for (const m of list) {
      const name = m.MakeName.trim().toUpperCase();
      if (name) all.add(name);
    }
  }

  const popular = POPULAR_MAKES.filter((m) => all.has(m));
  const other = Array.from(all)
    .filter((m) => !POPULAR_MAKES.includes(m))
    .sort();

  makesCache = { popular, other };
  sessionStorage.setItem('rapp_nhtsa_makes', JSON.stringify(makesCache));
  return makesCache;
}

const modelsCache = new Map<string, string[]>();

export async function fetchModels(make: string, year: string): Promise<string[]> {
  const key = `${make}|${year}`;
  const hit = modelsCache.get(key);
  if (hit) return hit;

  const results = await Promise.all(
    VEHICLE_TYPES.map((vt) =>
      vpicGet<{ Model_Name: string }>(
        `GetModelsForMakeYear/make/${encodeURIComponent(make.toLowerCase())}/modelyear/${year}/vehicletype/${encodeURIComponent(vt)}`
      )
    )
  );
  const all = new Set<string>();
  for (const list of results) {
    for (const m of list) {
      const name = m.Model_Name.trim();
      if (name) all.add(name);
    }
  }

  const models = Array.from(all).sort((a, b) => a.localeCompare(b));
  modelsCache.set(key, models);
  return models;
}

export const POWERTRAINS = [
  'Gasoline',
  'Diesel',
  'Hybrid',
  'Plug-in Hybrid',
  'Electric (EV)',
] as const;
