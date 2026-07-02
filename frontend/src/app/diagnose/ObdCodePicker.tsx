'use client';

import { useState, useRef } from 'react';
import { searchObdCodes, type ObdCode } from '@/lib/obdCodes';

interface ObdCodePickerProps {
  onSelect: (code: ObdCode) => void;
}

export default function ObdCodePicker({ onSelect }: ObdCodePickerProps) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [highlighted, setHighlighted] = useState(0);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const results = searchObdCodes(query);

  const selectCode = (code: ObdCode) => {
    onSelect(code);
    setQuery('');
    setOpen(false);
    setHighlighted(0);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!open || results.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlighted((h) => Math.min(h + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlighted((h) => Math.max(h - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      selectCode(results[highlighted]);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  return (
    <div className="obd-picker" ref={wrapperRef}>
      <label htmlFor="obd-code-input" className="sr-only">Search OBD-II codes</label>
      <input
        id="obd-code-input"
        data-testid="obd-code-input"
        className="input"
        type="text"
        placeholder="Search OBD-II code or description (e.g. P0301, misfire)"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          setHighlighted(0);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={handleKeyDown}
        autoComplete="off"
      />
      {open && results.length > 0 && (
        <ul className="obd-picker-results" data-testid="obd-code-results">
          {results.map((r, i) => (
            <li
              key={r.code}
              className={`obd-picker-result ${i === highlighted ? 'obd-picker-result-active' : ''}`}
              onMouseDown={() => selectCode(r)}
              onMouseEnter={() => setHighlighted(i)}
            >
              <span className="obd-picker-code">{r.code}</span>
              <span className="obd-picker-desc">{r.description}</span>
            </li>
          ))}
        </ul>
      )}
      {open && query.trim() && results.length === 0 && (
        <div className="obd-picker-results obd-picker-empty">No matching codes — type your own description below.</div>
      )}
    </div>
  );
}
