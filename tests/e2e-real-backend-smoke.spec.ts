import { test, expect } from '@playwright/test';

/**
 * Smoke test against the REAL FastAPI backend (backend/main.py, started with
 * ENVIRONMENT=test so it never dials out to live Gemini or a real ChromaDB --
 * see backend/core/config.py's `is_test_mode` and backend/rag/__init__.py /
 * backend/services/gemini.py) and the REAL Next.js frontend.
 *
 * This is deliberately NOT full parity with tests/e2e-mvp-flow.spec.ts:
 * that suite runs against tests/mock_app.py, a self-contained fake with its
 * own synthetic data/behavior. The real backend in test mode takes a
 * different code path for repair-step generation (MockVectorStore returns no
 * results, so backend/services/llm.py falls through to the curated template
 * library or the generic fallback steps -- see backend/repair_templates.py),
 * so this test only asserts the golden path renders and doesn't crash, not
 * exact copy/step content.
 *
 * VIN entry uses the Year/Make/Model cascade (not manual VIN text entry):
 * it produces a synthetic VIN decoded entirely client-side
 * (frontend/src/lib/vehicleSpecs.ts), so no live NHTSA call happens either --
 * keeping this test's only network dependency the app under test itself.
 */
test.describe('Real backend + real frontend smoke test', () => {
  test('VIN entry -> diagnose -> results -> paywall unlock -> repair', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.goto('/');

    // 1. Year/Make/Model cascade -> synthetic VIN, no NHTSA call.
    await page.locator('[data-testid="select-year"]').selectOption('2023');
    await page.locator('[data-testid="select-make"]').selectOption('HONDA');
    await page.locator('[data-testid="select-model"]').selectOption('ACCORD');

    const submitYmmBtn = page.locator('[data-testid="submit-ymm-btn"]');
    await expect(submitYmmBtn).toBeEnabled();
    await submitYmmBtn.click();
    await page.waitForURL(/\/diagnose/);

    const vin = await page.evaluate(() => localStorage.getItem('rapp_vin'));
    expect(vin).toBeTruthy();

    // 2. Diagnostic input: symptoms + tool constraints -> real POST /api/diagnose.
    await page.locator('[data-testid="symptoms-input"]').fill(
      'P0301 - Cylinder 1 Misfire Detected, rough idle'
    );
    await page.locator('[data-testid="tool-hand-tools"]').check();
    await page.locator('[data-testid="tool-jack-stands"]').check();

    const submitDiagnoseBtn = page.locator('[data-testid="submit-diagnose-btn"]');
    await submitDiagnoseBtn.click();
    await page.waitForURL(/\/results/);

    // 3. Free diagnosis summary renders (real /api/diagnose response), repair
    // steps are still gated behind the paywall CTA.
    await expect(page.locator('[data-testid="free-diagnosis-summary"]')).toBeVisible();
    await expect(page.locator('[data-testid="locked-repair-steps"]')).not.toBeVisible();

    const checkoutBtn = page.locator('[data-testid="payment-cta-btn"]');
    await expect(checkoutBtn).toBeVisible();
    await expect(checkoutBtn).toContainText(/Unlock/i);

    // 4. Simulate the Stripe success redirect -- /api/repair only requires a
    // non-empty stripe_session_id string (see backend/routers/repair.py),
    // it never calls out to real Stripe.
    await page.goto(
      `/repair/success?session_id=cs_test_real_backend_smoke&vin=${encodeURIComponent(vin!)}`
    );
    await page.waitForURL((url) => url.pathname === '/repair');

    const unlockedState = await page.evaluate(
      (v) => localStorage.getItem(`rapp_unlocked_${v}`),
      vin
    );
    expect(unlockedState).not.toBeNull();

    // 5. Real POST /api/repair response renders. In test mode this is the
    // template/generic fallback path (no Gemini, empty MockVectorStore), but
    // the contract (repair_steps: string[], citations: string[]) is the
    // same either way -- the page must render it without crashing.
    await expect(page.locator('[data-testid="detailed-repair-steps"]')).toBeVisible();
    await expect(page.locator('[data-testid="rag-citation"]').first()).toBeVisible();
  });
});
