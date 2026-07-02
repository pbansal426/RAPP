'use client';

import { useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Suspense } from 'react';

function SuccessHandler() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const vin = searchParams.get('vin');
    const sessionId = searchParams.get('session_id');
    if (vin && sessionId) {
      // Store the unlock token so the repair page can verify it
      localStorage.setItem(`rapp_unlocked_${vin}`, sessionId);
      // Also ensure the VIN is stored for the repair page
      localStorage.setItem('rapp_vin', vin);
    }
    router.replace('/repair');
  }, [searchParams, router]);

  return (
    <main className="page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ textAlign: 'center' }}>
        <p style={{ fontSize: '3rem', marginBottom: 16 }}>✅</p>
        <p style={{ color: 'var(--text-secondary)' }}>Payment confirmed — loading your repair guide…</p>
      </div>
    </main>
  );
}

export default function RepairSuccessPage() {
  return (
    <Suspense fallback={
      <main className="page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="loading-spinner" />
      </main>
    }>
      <SuccessHandler />
    </Suspense>
  );
}
