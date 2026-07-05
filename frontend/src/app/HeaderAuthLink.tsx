'use client';

import { useAuthUser } from '@/lib/auth';

export default function HeaderAuthLink() {
  const { user, loading, configured } = useAuthUser();
  if (!configured || loading) return null;

  const linkStyle = {
    fontSize: '0.82rem',
    fontWeight: 700,
    textDecoration: 'none',
    background: 'var(--bg-elevated)',
    border: '1px solid var(--border)',
    borderRadius: '100px',
    padding: '6px 14px',
  } as const;

  return (
    <div style={{ position: 'fixed', top: 14, right: 16, zIndex: 500, display: 'flex', gap: 8 }}>
      {user ? (
        <>
          <a href="/garage" style={{ ...linkStyle, color: 'var(--text-secondary)' }}>My Garage</a>
          <a href="/settings" style={{ ...linkStyle, color: 'var(--text-secondary)' }}>Settings</a>
        </>
      ) : (
        <a href="/signin" style={{ ...linkStyle, color: 'var(--accent-orange)' }}>Log In</a>
      )}
    </div>
  );
}
