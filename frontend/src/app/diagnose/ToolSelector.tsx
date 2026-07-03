'use client';

import { useState } from 'react';

interface ToolOption {
  id: string;
  category: 'brand' | 'hand' | 'diag' | 'power';
  label: string;
  tag?: string;
}

const ALL_TOOLS: ToolOption[] = [
  // Brands
  { id: 'brand-milwaukee', category: 'brand', label: 'Milwaukee M12/M18 Ecosystem' },
  { id: 'brand-dewalt', category: 'brand', label: 'DeWalt 20V MAX Ecosystem' },
  { id: 'brand-snapon', category: 'brand', label: 'Snap-on Professional Tools' },
  { id: 'brand-craftsman', category: 'brand', label: 'Craftsman Mechanics Set' },
  { id: 'brand-pittsburgh', category: 'brand', label: 'Harbor Freight / Pittsburgh / Icon' },

  // Hand & Mechanical Capabilities
  { id: 'tool-hand-tools', category: 'hand', label: 'Basic Hand Tools (Screwdrivers, Pliers)', tag: 'Basic' },
  { id: 'tool-socket-set', category: 'hand', label: 'Metric Deep & Shallow Socket Set (8mm–24mm)', tag: 'Metric' },
  { id: 'spec-imperial-sockets', category: 'hand', label: 'SAE / Imperial Socket Set', tag: 'SAE' },
  { id: 'spec-drive-38', category: 'hand', label: '3/8" Drive Ratchet & Extensions', tag: '3/8"' },
  { id: 'spec-drive-12', category: 'hand', label: '1/2" Heavy Duty Breaker Bar & Drive', tag: '1/2"' },
  { id: 'tool-torque-wrench', category: 'hand', label: 'Precision Click/Digital Torque Wrench (10–150 ft-lbs)', tag: 'Precision' },
  { id: 'spec-impact-sockets', category: 'hand', label: 'Impact-Rated Socket Set (Cr-Mo)', tag: 'Impact' },
  { id: 'tool-jack-stands', category: 'hand', label: 'Hydraulic Floor Jack & 3-Ton Jack Stands', tag: 'Safety' },

  // Diagnostics & Electrical
  { id: 'tool-obd-scanner', category: 'diag', label: 'Bidirectional / Live Data OBD-II Scanner', tag: 'Diag' },
  { id: 'tool-multimeter', category: 'diag', label: 'Digital Multimeter & Circuit Tester', tag: 'Elec' },

  // Power Tools
  { id: 'power-impact-wrench', category: 'power', label: 'Cordless High-Torque Impact Wrench', tag: 'Power' },
  { id: 'power-ratchet', category: 'power', label: 'Cordless Electric Ratchet', tag: 'Power' },
];

interface ToolSelectorProps {
  selectedTools: string[];
  onChange: (tools: string[]) => void;
}

export default function ToolSelector({ selectedTools, onChange }: ToolSelectorProps) {
  const [search, setSearch] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'brand' | 'capabilities'>('all');

  const toggleTool = (id: string) => {
    if (selectedTools.includes(id)) {
      onChange(selectedTools.filter((t) => t !== id));
    } else {
      onChange([...selectedTools, id]);
    }
  };

  const filtered = ALL_TOOLS.filter((t) => {
    const matchesSearch = t.label.toLowerCase().includes(search.toLowerCase());
    const matchesTab =
      activeTab === 'all' ||
      (activeTab === 'brand' && t.category === 'brand') ||
      (activeTab === 'capabilities' && t.category !== 'brand');
    return matchesSearch && matchesTab;
  });

  return (
    <div className="tool-selector">
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 12 }}>
        <input
          type="text"
          className="input"
          placeholder="Filter tool specs or brands (e.g. Milwaukee, Torque Wrench, Metric)..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ flex: '1 1 240px', fontSize: '0.875rem' }}
        />
        <div style={{ display: 'flex', gap: 6 }}>
          {(['all', 'brand', 'capabilities'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`btn ${activeTab === tab ? 'btn-primary' : 'btn-secondary'}`}
              style={{ padding: '6px 12px', fontSize: '0.8rem' }}
            >
              {tab === 'brand' ? 'Tool Brands' : tab === 'capabilities' ? 'Capabilities' : 'All'}
            </button>
          ))}
        </div>
      </div>

      <div
        className="checkbox-group"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: 10,
          maxHeight: 300,
          overflowY: 'auto',
          paddingRight: 4,
        }}
      >
        {filtered.map(({ id, label, tag }) => {
          const checked = selectedTools.includes(id);
          return (
            <label
              key={id}
              htmlFor={id}
              className="checkbox-label"
              style={{
                height: 'auto',
                minHeight: 48,
                padding: '10px 14px',
                borderColor: checked ? 'var(--accent-orange)' : 'var(--border)',
                background: checked ? 'rgba(249, 115, 22, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <input
                  type="checkbox"
                  id={id}
                  data-testid={id}
                  checked={checked}
                  onChange={() => toggleTool(id)}
                />
                <span style={{ fontSize: '0.875rem', fontWeight: checked ? 600 : 400, color: 'var(--text-primary)' }}>
                  {label}
                </span>
              </div>
              {tag && (
                <span style={{ fontSize: '0.72rem', background: 'rgba(255,255,255,0.06)', padding: '2px 6px', borderRadius: 4, color: 'var(--text-secondary)' }}>
                  {tag}
                </span>
              )}
            </label>
          );
        })}
      </div>
      {selectedTools.length > 0 && (
        <p className="text-muted text-sm" style={{ marginTop: 10 }}>
          ✓ {selectedTools.length} professional tool profile{selectedTools.length === 1 ? '' : 's'} active for AI diagnosis matching.
        </p>
      )}
    </div>
  );
}
