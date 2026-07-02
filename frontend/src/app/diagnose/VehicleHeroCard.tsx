'use client';

import { useState } from 'react';
import { getLogoUrl } from '@/lib/logos';

interface VehicleHeroCardProps {
  vin: string;
  vinData: Record<string, unknown> | null;
}

function GenericVehicleIcon() {
  return (
    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path
        d="M4 16.5V11l1.8-4.6A2 2 0 0 1 7.66 5h8.68a2 2 0 0 1 1.86 1.4L20 11v5.5"
        stroke="var(--accent-orange)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"
      />
      <path d="M4 11h16" stroke="var(--accent-orange)" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="7.5" cy="16.5" r="1.7" stroke="var(--accent-orange)" strokeWidth="1.6" />
      <circle cx="16.5" cy="16.5" r="1.7" stroke="var(--accent-orange)" strokeWidth="1.6" />
      <path d="M4 16.5h1.8M18.2 16.5H20" stroke="var(--accent-orange)" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export default function VehicleHeroCard({ vin, vinData }: VehicleHeroCardProps) {
  const [logoFailed, setLogoFailed] = useState(false);
  if (!vinData) return null;

  const year = String(vinData.year ?? '').trim();
  const make = String(vinData.make ?? '').trim();
  const model = String(vinData.model ?? '').trim();
  const engine = String(vinData.engine ?? '').trim();
  const drive = String(vinData.drive_type ?? vinData.drive ?? '').trim();
  const logoUrl = getLogoUrl(make);
  const title = [year, make, model].filter(Boolean).join(' ') || 'Vehicle Identified';

  return (
    <div className="vehicle-hero">
      <div className="vehicle-hero-logo">
        {logoUrl && !logoFailed ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={logoUrl} alt={`${make} logo`} onError={() => setLogoFailed(true)} />
        ) : (
          <GenericVehicleIcon />
        )}
      </div>
      <div className="vehicle-hero-info">
        <span className="badge badge-free">✓ Vehicle Found</span>
        <h2 className="vehicle-hero-title">{title}</h2>
        <p className="vehicle-hero-sub">
          {engine && <span>{engine}</span>}
          {drive && <span> • {drive}</span>}
          <span> • VIN {vin}</span>
        </p>
      </div>
    </div>
  );
}
