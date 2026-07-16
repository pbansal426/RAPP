'use client';

import { useState } from 'react';
import type { RecommendedPart } from '@/lib/types';

interface PartsPurchasePlanProps {
  parts: RecommendedPart[];
  vehicleTitle?: string;
  guideFee?: number;
}

interface DisplayOption {
  title: string;
  brand: string;
  estimated_price: number;
  rationale: string;
  purchase_url: string;
  part_number: string | null;
  isOem: boolean;
}

// Shapes the 3-tier backend options into the OEM-vs-Aftermarket pair shown in
// the dashboard, with friendlier copy for fluids/filters where "OEM" reads
// oddly.
function buildDisplayOptions(part: RecommendedPart): DisplayOption[] {
  const isOilFluidFilter = /(oil|fluid|filter)/i.test(part.part_name);
  const oemOpt = part.options.find((o) => o.tier === 'OEM');
  const aftermarketOpt = part.options.find((o) => o.tier === 'Aftermarket / Budget');

  const opt1 = oemOpt || part.options[0];
  const opt2 = aftermarketOpt || part.options[1] || part.options[0];

  const opt1Brand = isOilFluidFilter && opt1?.brand === 'OEM / Genuine Dealer Part' ? 'Mobil 1 / Castrol' : (opt1?.brand || 'OEM Factory');
  const opt2Brand = isOilFluidFilter && opt2?.brand === 'Duralast / equivalent aftermarket' ? 'Valvoline / Pennzoil' : (opt2?.brand || 'Premium Aftermarket');

  const opt1Rationale = isOilFluidFilter && opt1?.rationale.includes('factory fit')
    ? 'Full synthetic formulation providing superior thermal stability, oxidation resistance, and extended engine protection.'
    : (opt1?.rationale || 'Exact factory spec and fitment.');
  const opt2Rationale = isOilFluidFilter && opt2?.rationale.includes('daily-driver')
    ? 'Conventional mineral-based formulation meeting basic API specifications for standard drain intervals.'
    : (opt2?.rationale || 'High-quality aftermarket replacement.');

  return [
    {
      title: isOilFluidFilter ? 'Premium Synthetic Oil' : 'OEM Factory Part',
      brand: opt1Brand,
      estimated_price: opt1?.estimated_price ?? 0,
      rationale: opt1Rationale,
      purchase_url: opt1?.purchase_url || '',
      part_number: opt1?.part_number || null,
      isOem: true,
    },
    {
      title: isOilFluidFilter ? 'Standard Conventional Oil' : 'Premium Aftermarket',
      brand: opt2Brand,
      estimated_price: opt2?.estimated_price ?? 0,
      rationale: opt2Rationale,
      purchase_url: opt2?.purchase_url || '',
      part_number: opt2?.part_number || null,
      isOem: false,
    },
  ];
}

export default function PartsPurchasePlan({ parts, vehicleTitle, guideFee = 4.99 }: PartsPurchasePlanProps) {
  // Per-part tier selection: index into buildDisplayOptions (0 = OEM,
  // 1 = Aftermarket). Defaults to Aftermarket so the initial total agrees
  // with the backend's budget-tier diy_total.
  const [selections, setSelections] = useState<Record<number, number>>({});

  if (!parts || parts.length === 0) return null;

  const selectedFor = (partIdx: number) => selections[partIdx] ?? 1;
  const partsTotal = parts.reduce((sum, part, idx) => {
    const opts = buildDisplayOptions(part);
    return sum + (opts[selectedFor(idx)]?.estimated_price ?? 0);
  }, 0);
  const diyTotal = guideFee + partsTotal;

  return (
    <div className="parts-purchase-plan" style={{ marginTop: 28 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', marginBottom: 16 }}>
        <div>
          <h2 className="section-title" style={{ margin: 0 }}>Verified Parts &amp; Tool Purchase Recommendations</h2>
          <p className="text-muted text-sm" style={{ marginTop: 4 }}>
            Curated engineering tiers specifically matched to your {vehicleTitle ?? 'vehicle'}. Tap a tier to build your parts budget.
          </p>
        </div>
        <span className="badge badge-pro">1-Click Affiliate Matching</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {parts.map((part, idx) => {
          const displayOptions = buildDisplayOptions(part);
          const selectedIdx = selectedFor(idx);

          return (
            <div
              key={`${part.part_name}-${idx}`}
              className="card"
              style={{
                padding: 20,
                background: 'linear-gradient(145deg, rgba(30, 41, 59, 0.4), rgba(15, 23, 42, 0.7))',
                border: '1px solid rgba(255, 255, 255, 0.08)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                  {part.part_name}
                </h3>
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                  gap: 14,
                }}
              >
                {displayOptions.map((opt, optIdx) => {
                  const isSelected = selectedIdx === optIdx;
                  const badgeBg = opt.isOem ? 'rgba(59, 130, 246, 0.15)' : 'rgba(34, 197, 94, 0.15)';
                  const badgeColor = opt.isOem ? '#60a5fa' : '#4ade80';

                  return (
                    <div
                      key={`${opt.title}-${optIdx}`}
                      role="radio"
                      aria-checked={isSelected}
                      tabIndex={0}
                      onClick={() => setSelections((prev) => ({ ...prev, [idx]: optIdx }))}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setSelections((prev) => ({ ...prev, [idx]: optIdx }));
                        }
                      }}
                      style={{
                        background: isSelected ? 'rgba(249, 115, 22, 0.06)' : 'rgba(255, 255, 255, 0.03)',
                        border: `1px solid ${isSelected ? 'var(--accent-orange)' : opt.isOem ? 'rgba(59, 130, 246, 0.3)' : 'rgba(255, 255, 255, 0.08)'}`,
                        borderRadius: 12,
                        padding: 16,
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                        transition: 'border-color 0.15s ease, background 0.15s ease',
                      }}
                    >
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                          <span
                            style={{
                              background: badgeBg,
                              color: badgeColor,
                              padding: '3px 10px',
                              borderRadius: 6,
                              fontSize: '0.75rem',
                              fontWeight: 700,
                              letterSpacing: '0.03em',
                              textTransform: 'uppercase',
                            }}
                          >
                            {opt.title}
                          </span>
                          <span style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                            ${opt.estimated_price ? opt.estimated_price.toFixed(2) : '0.00'}
                          </span>
                        </div>

                        <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 6px' }}>
                          {opt.brand && <span style={{ color: 'var(--accent-orange)' }}>{opt.brand} </span>}
                          {isSelected && (
                            <span style={{ color: '#4ade80', fontSize: '0.78rem', fontWeight: 700, marginLeft: 4 }}>In your plan</span>
                          )}
                        </h4>

                        {opt.part_number && (
                          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '0 0 8px', fontFamily: 'monospace' }}>
                            P/N: {opt.part_number}
                          </p>
                        )}

                        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4, margin: '0 0 16px' }}>
                          {opt.rationale}
                        </p>
                      </div>

                      <a
                        href={opt.purchase_url || `https://www.amazon.com/s?k=${encodeURIComponent(`${part.part_name} ${opt.brand || ''} ${opt.part_number || ''}`)}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={`btn ${opt.isOem ? 'btn-primary' : 'btn-secondary'}`}
                        onClick={(e) => e.stopPropagation()}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: 8,
                          padding: '10px',
                          fontSize: '0.85rem',
                          textDecoration: 'none',
                        }}
                      >
                        <span>{opt.purchase_url?.includes('rockauto') ? 'Buy OEM on RockAuto' : opt.purchase_url?.includes('autozone') ? 'Find at AutoZone' : 'Buy on Amazon'}</span>
                        <span aria-hidden="true">↗</span>
                      </a>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Live DIY budget from the selected tiers ── */}
      <div
        className="card"
        data-testid="parts-plan-total"
        style={{
          marginTop: 16,
          padding: '16px 20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 10,
          border: '1px solid var(--accent-orange)',
        }}
      >
        <div>
          <p className="card-label" style={{ margin: 0, color: 'var(--accent-orange)' }}>Your DIY Parts Budget</p>
          <p className="text-muted text-sm" style={{ margin: '4px 0 0' }}>
            Selected parts ${partsTotal.toFixed(2)} + ${guideFee.toFixed(2)} RAPP guide fee
          </p>
        </div>
        <span style={{ fontSize: '1.5rem', fontWeight: 900, color: 'var(--text-primary)' }}>
          ${diyTotal.toFixed(2)}
        </span>
      </div>
    </div>
  );
}
