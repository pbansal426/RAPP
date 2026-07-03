/**
 * Curated vehicle-spec lookup for the home page's Year/Make/Model/Trim
 * selector. NHTSA's vPIC API cannot resolve powertrain/engine/drive per
 * *trim* (that data is manufacturer-proprietary), so this table hand-curates
 * popular North American vehicles whose specs are unambiguous for a given
 * year/make/model(/trim) combination.
 *
 * When `lookupVehicleSpecs` returns a hit, the UI auto-populates and locks
 * the matched fields instead of asking the user; a miss simply leaves the
 * manual selectors enabled. Only fields present on an entry are locked —
 * e.g. a 4Runner entry can lock engine ("4.0L V6") while leaving drive type
 * (RWD vs 4WD) to the user.
 */

export interface VehicleSpecMatch {
  powertrain?: string; // one of nhtsa.ts POWERTRAINS
  engine?: string;     // short human string, e.g. "1.8L I4"
  drive_type?: string; // FWD | RWD | AWD | 4WD
}

interface VehicleSpecEntry extends VehicleSpecMatch {
  make: string;          // uppercase
  model: string;         // uppercase
  trim?: string;         // uppercase; omitted = applies to every trim
  years: [number, number]; // inclusive range
}

const SPEC_TABLE: VehicleSpecEntry[] = [
  // ── Toyota ──
  { make: 'TOYOTA', model: 'COROLLA', years: [2009, 2013], powertrain: 'Gasoline', engine: '1.8L I4', drive_type: 'FWD' },
  { make: 'TOYOTA', model: 'COROLLA', years: [2014, 2019], powertrain: 'Gasoline', engine: '1.8L I4', drive_type: 'FWD' },
  { make: 'TOYOTA', model: 'CAMRY', years: [2007, 2017], powertrain: 'Gasoline' },
  { make: 'TOYOTA', model: 'HIGHLANDER', trim: 'XLE', years: [2014, 2016], powertrain: 'Gasoline', engine: '3.5L V6', drive_type: 'AWD' },
  { make: 'TOYOTA', model: 'HIGHLANDER', trim: 'LIMITED', years: [2014, 2016], powertrain: 'Gasoline', engine: '3.5L V6', drive_type: 'AWD' },
  { make: 'TOYOTA', model: 'PRIUS', years: [2010, 2015], powertrain: 'Hybrid', engine: '1.8L I4 Hybrid', drive_type: 'FWD' },
  { make: 'TOYOTA', model: '4RUNNER', years: [2010, 2023], powertrain: 'Gasoline', engine: '4.0L V6' },
  { make: 'TOYOTA', model: 'TACOMA', years: [2016, 2023], powertrain: 'Gasoline' },
  { make: 'TOYOTA', model: 'RAV4', years: [2013, 2018], powertrain: 'Gasoline', engine: '2.5L I4' },

  // ── Honda ──
  { make: 'HONDA', model: 'CIVIC', trim: 'LX', years: [2006, 2011], powertrain: 'Gasoline', engine: '1.8L I4', drive_type: 'FWD' },
  { make: 'HONDA', model: 'CIVIC', trim: 'EX', years: [2006, 2011], powertrain: 'Gasoline', engine: '1.8L I4', drive_type: 'FWD' },
  { make: 'HONDA', model: 'CIVIC', trim: 'SI', years: [2006, 2011], powertrain: 'Gasoline', engine: '2.0L I4', drive_type: 'FWD' },
  { make: 'HONDA', model: 'FIT', years: [2009, 2020], powertrain: 'Gasoline', engine: '1.5L I4', drive_type: 'FWD' },
  { make: 'HONDA', model: 'CR-V', years: [2007, 2014], powertrain: 'Gasoline', engine: '2.4L I4' },
  { make: 'HONDA', model: 'ACCORD', trim: 'SPORT', years: [2013, 2017], powertrain: 'Gasoline', engine: '2.4L I4', drive_type: 'FWD' },
  { make: 'HONDA', model: 'ODYSSEY', years: [2005, 2023], powertrain: 'Gasoline', engine: '3.5L V6', drive_type: 'FWD' },

  // ── Ford ──
  { make: 'FORD', model: 'MUSTANG', trim: 'GT', years: [2011, 2023], powertrain: 'Gasoline', engine: '5.0L V8', drive_type: 'RWD' },
  { make: 'FORD', model: 'MUSTANG', trim: 'ECOBOOST', years: [2015, 2023], powertrain: 'Gasoline', engine: '2.3L I4 Turbo', drive_type: 'RWD' },
  { make: 'FORD', model: 'FOCUS', trim: 'ST', years: [2013, 2018], powertrain: 'Gasoline', engine: '2.0L I4 Turbo', drive_type: 'FWD' },
  { make: 'FORD', model: 'FOCUS', years: [2012, 2018], powertrain: 'Gasoline', drive_type: 'FWD' },
  { make: 'FORD', model: 'F-150', years: [1990, 2017], powertrain: 'Gasoline' },
  { make: 'FORD', model: 'ESCAPE', years: [2013, 2019], powertrain: 'Gasoline' },

  // ── Chevrolet ──
  { make: 'CHEVROLET', model: 'CORVETTE', years: [2008, 2013], powertrain: 'Gasoline', engine: '6.2L V8', drive_type: 'RWD' },
  { make: 'CHEVROLET', model: 'CRUZE', trim: 'LS', years: [2011, 2015], powertrain: 'Gasoline', engine: '1.8L I4', drive_type: 'FWD' },
  { make: 'CHEVROLET', model: 'CRUZE', trim: 'LT', years: [2011, 2015], powertrain: 'Gasoline', engine: '1.4L I4 Turbo', drive_type: 'FWD' },
  { make: 'CHEVROLET', model: 'BOLT EV', years: [2017, 2023], powertrain: 'Electric (EV)', engine: 'Electric Motor', drive_type: 'FWD' },
  { make: 'CHEVROLET', model: 'VOLT', years: [2016, 2019], powertrain: 'Plug-in Hybrid', engine: '1.5L I4 Range Extender', drive_type: 'FWD' },
  { make: 'CHEVROLET', model: 'MALIBU', years: [2013, 2015], powertrain: 'Gasoline', drive_type: 'FWD' },
];

/** Trim choices offered per model in the manual selector. Falls back to a
 * generic list for models we haven't curated. */
export function getTrimsForModel(model: string): string[] {
  const upper = model.toUpperCase();
  if (upper.includes('COROLLA')) return ['Base', 'S', 'LE', 'XLE'];
  if (upper.includes('HIGHLANDER')) return ['Base', 'LE', 'XLE', 'Limited'];
  if (upper.includes('ACCORD')) return ['Base', 'Sport', 'Touring'];
  if (upper.includes('CIVIC')) return ['Base', 'LX', 'EX', 'Si'];
  if (upper.includes('MUSTANG')) return ['Base', 'EcoBoost', 'GT'];
  if (upper.includes('CRUZE')) return ['Base', 'LS', 'LT', 'LTZ'];
  if (upper.includes('FOCUS')) return ['Base', 'S', 'SE', 'ST'];
  return ['Base', 'S', 'LE', 'XLE', 'Sport', 'Touring'];
}

/**
 * Returns the locked specs for a year/make/model/trim combination, or null
 * when the vehicle isn't in the curated table (leave manual selectors on).
 * Trim-specific entries take precedence over all-trim entries.
 */
export function lookupVehicleSpecs(
  year: string | number,
  make: string,
  model: string,
  trim: string,
): VehicleSpecMatch | null {
  const y = Number(year);
  if (!Number.isFinite(y)) return null;
  const makeU = make.trim().toUpperCase();
  const modelU = model.trim().toUpperCase();
  const trimU = trim.trim().toUpperCase();

  const candidates = SPEC_TABLE.filter(
    (e) =>
      e.make === makeU &&
      e.model === modelU &&
      y >= e.years[0] &&
      y <= e.years[1] &&
      (e.trim === undefined || e.trim === trimU),
  );
  if (candidates.length === 0) return null;

  // Prefer the trim-specific entry when both a trim-specific and an
  // all-trims entry match.
  const best = candidates.find((e) => e.trim !== undefined) ?? candidates[0];
  const { powertrain, engine, drive_type } = best;
  return { powertrain, engine, drive_type };
}
