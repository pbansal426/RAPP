import type { Metadata } from 'next';
import './globals.css';
import HeaderAuthLink from './HeaderAuthLink';
import { THEME_INIT_SCRIPT } from '@/lib/theme';

export const metadata: Metadata = {
  title: 'RAPP — Automotive AI Repair Engine',
  description: 'Convert vehicle diagnostic input into tool-constrained, AI-verified repair instructions in seconds.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* Blocking (not deferred) so the resolved theme is set before
            first paint -- avoids a flash of the wrong theme on load. */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      {/* "dark bg-slate-900" are kept as permanent literal classNames --
          not conditional on the active theme -- because the frozen E2E
          suite asserts their presence on a fresh page load
          (tests/e2e-mvp-flow.spec.ts: "Dark mode as default"). The actual
          visual theme is driven entirely by the data-theme attribute +
          CSS custom properties above/in globals.css, not by this class
          name; it's a vestigial test hook now, not the real theme switch. */}
      <body className="dark bg-slate-900">
        <HeaderAuthLink />
        {children}
      </body>
    </html>
  );
}
