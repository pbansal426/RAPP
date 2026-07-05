import { defineConfig, devices } from '@playwright/test';

/**
 * Config for the "real backend" CI smoke test (see .github/workflows/ci.yml
 * job `e2e-real-backend`). This runs a single focused spec
 * (tests/e2e-real-backend-smoke.spec.ts) against the REAL FastAPI backend
 * (backend/main.py, ENVIRONMENT=test so no live Gemini/ChromaDB) and the
 * REAL Next.js frontend -- as opposed to the main playwright.config.ts,
 * which targets tests/e2e-mvp-flow.spec.ts against tests/mock_app.py's
 * self-contained fake.
 *
 * playwright.config.ts's testIgnore excludes e2e-real-backend-smoke.spec.ts
 * so the two suites never overlap: the mock-app suite (run via
 * tests/verify_tests.sh and the `e2e-tests` CI job) never picks up this
 * spec, and this config only ever picks up this one spec.
 */
export default defineConfig({
  testDir: './tests',
  testMatch: ['e2e-real-backend-smoke.spec.ts'],
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: 'html',
  use: {
    baseURL: process.env.FRONTEND_URL || 'http://localhost:3100',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
