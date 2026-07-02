import type { Metadata } from 'next';
import './globals.css';
import HeaderAuthLink from './HeaderAuthLink';

export const metadata: Metadata = {
  title: 'RAPP — Automotive AI Repair Engine',
  description: 'Convert vehicle diagnostic input into tool-constrained, AI-verified repair instructions in seconds.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="dark bg-slate-900">
        <HeaderAuthLink />
        {children}
      </body>
    </html>
  );
}
