'use client';

import { useAuthUser } from '@/lib/auth';

export default function HeaderAuthLink() {
  const { user, loading, configured } = useAuthUser();
  if (!configured || loading) return null;

  return (
    <div style={{ position: 'fixed', top: 14, right: 16, zIndex: 500 }}>
      <a
        href="/garage"
        style={{
          fontSize: '0.82rem',
          fontWeight: 700,
          color: user ? 'var(--text-secondary)' : 'var(--accent-orange)',
          textDecoration: 'none',
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          borderRadius: '100px',
          padding: '6px 14px',
        }}
      >
        {user ? 'My Garage' : 'Log In'}
      </a>
    </div>
  );
}
