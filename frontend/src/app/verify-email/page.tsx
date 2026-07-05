'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { verifyEmail } from '@/lib/auth';
import { AppLogoMarkIcon, CheckCircleIcon } from '@/app/sharedIcons';

function VerifyEmailHandler() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const [status, setStatus] = useState<'pending' | 'success' | 'error'>('pending');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setError('This verification link is missing its token.');
      return;
    }
    verifyEmail(token)
      .then(() => setStatus('success'))
      .catch((err) => {
        setStatus('error');
        setError(err instanceof Error ? err.message : 'Could not verify your email. The link may have expired.');
      });
  }, [token]);

  return (
    <main className="page">
      <header className="page-header">
        <div className="logo"><AppLogoMarkIcon size={20} /><span>RAPP</span></div>
        <h1 className="page-title">Email Verification</h1>
      </header>

      <div className="card" style={{ textAlign: 'center' }}>
        {status === 'pending' && <div className="loading-spinner" style={{ margin: '0 auto' }} />}
        {status === 'success' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center' }}>
            <CheckCircleIcon size={28} style={{ color: '#4ade80' }} />
            <p style={{ fontWeight: 700 }}>Your email is verified.</p>
            <a href="/settings" className="btn btn-primary" style={{ width: 'auto', padding: '0 18px' }}>Go to Settings →</a>
          </div>
        )}
        {status === 'error' && <p style={{ color: 'var(--accent-red)' }}>{error}</p>}
      </div>
    </main>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <main className="page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="loading-spinner" />
      </main>
    }>
      <VerifyEmailHandler />
    </Suspense>
  );
}
