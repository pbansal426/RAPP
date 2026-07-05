'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { forgotPassword } from '@/lib/auth';
import { AppLogoMarkIcon } from '@/app/sharedIcons';

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ message: string; resetLink: string | null } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await forgotPassword(email.trim());
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="page">
      <div style={{ display: 'flex', width: '100%', justifyContent: 'flex-start', marginBottom: 12 }}>
        <button
          className="btn btn-secondary"
          type="button"
          onClick={() => router.push('/signin')}
          style={{ padding: '6px 12px', fontSize: '0.875rem' }}
        >
          ← Back to Log In
        </button>
      </div>

      <header className="page-header">
        <div className="logo"><AppLogoMarkIcon size={20} /><span>RAPP</span></div>
        <h1 className="page-title">Reset Password</h1>
        <p className="page-subtitle">Enter your account email to get a reset link.</p>
      </header>

      <div className="card">
        {result ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <p className="card-label">Check your reset link</p>
            <p className="text-muted text-sm">{result.message}</p>
            {result.resetLink && (
              <>
                <p className="text-muted text-sm" style={{ marginTop: 4 }}>
                  No email provider is configured yet, so here&apos;s your link directly:
                </p>
                <a href={result.resetLink} className="btn btn-primary" style={{ width: 'auto', padding: '0 18px' }}>
                  Reset Your Password →
                </a>
              </>
            )}
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <label htmlFor="forgot-email" className="sr-only">Email</label>
            <input
              id="forgot-email"
              className="input"
              type="email"
              placeholder="Email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            {error && <p style={{ color: 'var(--accent-red)', fontSize: '0.85rem' }}>{error}</p>}
            <button type="submit" className="btn btn-primary" disabled={submitting || !email.trim()}>
              {submitting ? <><span className="loading-spinner" aria-hidden="true" /> Sending…</> : 'Send Reset Link'}
            </button>
          </form>
        )}
      </div>
    </main>
  );
}
