'use client';

import { useRouter } from 'next/navigation';
import { AppLogoMarkIcon } from '@/app/sharedIcons';

export default function PrivacyPage() {
  const router = useRouter();

  return (
    <main className="page" style={{ maxWidth: '800px', margin: '40px auto', padding: '0 20px' }}>
      <button 
        className="btn btn-secondary" 
        onClick={() => router.back()} 
        style={{ marginBottom: '24px', width: 'auto', padding: '8px 16px' }}
      >
        ← Go Back
      </button>

      <header className="page-header" style={{ marginBottom: '32px' }}>
        <div className="logo"><AppLogoMarkIcon size={24} /><span>RAPP</span></div>
        <h1 className="page-title" style={{ fontSize: '2.5rem', fontWeight: 900, marginTop: '16px' }}>Privacy Policy</h1>
        <p className="text-muted">Last Updated: July 15, 2026</p>
      </header>

      <div className="card" style={{ padding: '32px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <section>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>1. Information We Collect</h2>
          <p className="text-muted" style={{ lineHeight: '1.6' }}>
            To generate and persist clinic-grade repair and diagnostic guides, we collect certain information about your vehicle and activities. This includes vehicle identification numbers (VINs), year, make, model, trim, and powertrain specifications, diagnostic trouble codes (OBD-II), reported symptoms, and tool compatibility selections.
          </p>
        </section>

        <section>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>2. Data Retention & Garage Profiles</h2>
          <p className="text-muted" style={{ lineHeight: '1.6' }}>
            If you create a Garage Account, we persist your email address, display name, vehicle profiles, and generated repair guides. This data is securely stored on our servers to allow you to access your guides from any device. We do not sell or lease your personal or vehicle data to third parties.
          </p>
        </section>

        <section>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>3. Third-Party Integrations & Payments</h2>
          <p className="text-muted" style={{ lineHeight: '1.6' }}>
            Payment processing is handled securely via Stripe/Polar integrations. We do not store or process your raw credit card numbers or financial passwords. Additionally, third-party lookups (such as the NHTSA recall/complaints APIs) are utilized live, and lookups do not transmit personally identifying user credentials.
          </p>
        </section>

        <section>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>4. Security Measures</h2>
          <p className="text-muted" style={{ lineHeight: '1.6' }}>
            We implement industry-standard encryption protocols (HTTPS/TLS) for data in transit. Accounts are secured using bearer tokens (JWTs) generated server-side.
          </p>
        </section>
      </div>
    </main>
  );
}
