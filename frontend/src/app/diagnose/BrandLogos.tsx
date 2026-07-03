'use client';

import React from 'react';

// Toyota: Three overlapping ellipses
export function ToyotaLogo(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <ellipse cx="12" cy="12" rx="11" ry="7" />
      <ellipse cx="12" cy="12" rx="4" ry="7" />
      <ellipse cx="12" cy="10" rx="8" ry="3.5" />
    </svg>
  );
}

// Honda: Stylized H inside rounded rectangle
export function HondaLogo(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <rect x="3" y="3" width="18" height="18" rx="3" />
      <path d="M7 6v11a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V6" />
      <path d="M7 11h10" />
    </svg>
  );
}

// Ford: Script/oval shape
export function FordLogo(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <ellipse cx="12" cy="12" rx="11" ry="6" />
      <path d="M8 14.5c1.2-0.8 2-2 2.5-3.5H9v-1h1.5c0.1-1 .5-2 1.5-2s1.5.5 1.5 1.5c0 .4-.1.8-.2 1.2h2.2v0.8H13c-.2 1.2-.8 2.4-1.8 3.2h3" />
    </svg>
  );
}

// Chevrolet: Classic bowtie
export function ChevroletLogo(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d="M7.7 8.3L9 6.5h6l1.3 1.8H22v4.4h-5.7L15 14.5H9l-1.3-1.8H2v-4.4h5.7z" />
    </svg>
  );
}

// Nissan: Circle with horizontal NISSAN banner
export function NissanLogo(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 10h18v4H3z" fill="rgba(15, 23, 42, 0.9)" />
      <path d="M3 10h18v4H3z" />
      <path d="M5 13V11l2 2V11 M8.5 11v2 M10.5 13h1.5v-1H10.5v-1h1.5 M13.5 13h1.5v-1H13.5v-1h1.5 M16.5 13l1-2 1 2 M16.8 12.2h1.4 M19.5 13V11l2 2V11" strokeWidth="1" />
    </svg>
  );
}

// Jeep: Front grille with round headlights
export function JeepLogo(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="4" cy="12" r="2" />
      <circle cx="20" cy="12" r="2" />
      <rect x="7" y="9" width="1" height="6" rx="0.5" fill="currentColor" />
      <rect x="9.2" y="9" width="1" height="6" rx="0.5" fill="currentColor" />
      <rect x="11.4" y="9" width="1" height="6" rx="0.5" fill="currentColor" />
      <rect x="13.6" y="9" width="1" height="6" rx="0.5" fill="currentColor" />
      <rect x="15.8" y="9" width="1" height="6" rx="0.5" fill="currentColor" />
      <rect x="7" y="9" width="1" height="6" rx="0.5" />
      <rect x="9.2" y="9" width="1" height="6" rx="0.5" />
      <rect x="11.4" y="9" width="1" height="6" rx="0.5" />
      <rect x="13.6" y="9" width="1" height="6" rx="0.5" />
      <rect x="15.8" y="9" width="1" height="6" rx="0.5" />
      <path d="M2 16h20" strokeWidth="1.5" />
    </svg>
  );
}

// BMW: Circle with quadrants
export function BmwLogo(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="12" cy="12" r="11" />
      <circle cx="12" cy="12" r="7" />
      <path d="M12 5v14M5 12h14" />
      <path d="M12 12h7A7 7 0 0 0 12 5v7z" fill="currentColor" className="text-blue-500" />
      <path d="M12 12H5a7 7 0 0 0 7 7v-7z" fill="currentColor" className="text-blue-500" />
    </svg>
  );
}

// Mercedes-Benz: Three-pointed star in a circle
export function MercedesLogo(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="12" cy="12" r="11" />
      <path d="M12 12V1.5" />
      <path d="M12 12l9.5 5.5" />
      <path d="M12 12L2.5 17.5" />
    </svg>
  );
}

// Tesla: Stylized T
export function TeslaLogo(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d="M12 2.5c-3.2 0-6.3-.7-8-1.5 0 .2.1.4.1.6 0 3.2 2 6 5.4 6.9L7.5 19.5c1.8.8 3.5 1.2 4.5 1.3 1-.1 2.7-.5 4.5-1.3l-2-11c3.4-.9 5.4-3.7 5.4-6.9 0-.2.1-.4.1-.6-1.7.8-4.8 1.5-8 1.5z" />
    </svg>
  );
}

export function getBrandLogoSvg(make: string): React.ReactNode | null {
  const norm = make.trim().toUpperCase();
  
  switch (norm) {
    case 'TOYOTA':
      return <ToyotaLogo className="w-14 h-14 text-red-500 stroke-red-500" />;
    case 'HONDA':
      return <HondaLogo className="w-14 h-14 text-slate-300 stroke-slate-300" />;
    case 'FORD':
      return <FordLogo className="w-14 h-14 text-blue-500 stroke-blue-500" />;
    case 'CHEVROLET':
      return <ChevroletLogo className="w-14 h-14 text-yellow-500" />;
    case 'NISSAN':
      return <NissanLogo className="w-14 h-14 text-slate-300 stroke-slate-300" />;
    case 'JEEP':
      return <JeepLogo className="w-14 h-14 text-green-600 stroke-green-600" />;
    case 'BMW':
      return <BmwLogo className="w-14 h-14 text-slate-100 stroke-slate-100" />;
    case 'MERCEDES-BENZ':
    case 'MERCEDES':
      return <MercedesLogo className="w-14 h-14 text-slate-300 stroke-slate-300" />;
    case 'TESLA':
      return <TeslaLogo className="w-14 h-14 text-red-600" />;
    default:
      return null;
  }
}
