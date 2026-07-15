'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ARTICLES, Article } from './articles';

const CATEGORIES: Array<Article['category'] | 'All'> = [
  'All',
  'Maintenance',
  'Diagnostics',
  'Buying a Guide',
  'Safety',
];

export default function HubPage() {
  const [activeCategory, setActiveCategory] = useState<Article['category'] | 'All'>('All');

  const visible =
    activeCategory === 'All'
      ? ARTICLES
      : ARTICLES.filter((a) => a.category === activeCategory);

  return (
    <main className="hub-page">
      <div className="hub-header">
        <h1>Knowledge Hub</h1>
        <p className="hub-subtitle">
          Straight answers on car care, diagnostics, and fair pricing -- verified against OEM
          service data, not guessed.
        </p>
      </div>

      <div className="hub-filter-row" role="tablist" aria-label="Filter articles by category">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            role="tab"
            aria-selected={activeCategory === cat}
            className={`hub-filter-chip${activeCategory === cat ? ' hub-filter-chip-active' : ''}`}
            onClick={() => setActiveCategory(cat)}
          >
            {cat}
          </button>
        ))}
      </div>

      <div className="hub-grid">
        {visible.map((article) => (
          <Link key={article.slug} href={`/hub/${article.slug}`} className="hub-card">
            <span className="hub-card-category">{article.category}</span>
            <h2 className="hub-card-title">{article.title}</h2>
            <p className="hub-card-summary">{article.summary}</p>
            <span className="hub-card-meta">{article.readMinutes} min read</span>
          </Link>
        ))}
      </div>

      <Link href="/" className="hub-back-link">
        Back to RAPP
      </Link>
    </main>
  );
}
