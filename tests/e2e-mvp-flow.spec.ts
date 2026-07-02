import { test, expect } from '@playwright/test';

test.describe('Automotive AI Repair Engine - Phase 1 MVP Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Clear localStorage to start with a clean state
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('Step 1: Frictionless VIN Ingestion', async ({ page }) => {
    await page.goto('/');

    // 1. Verify Greasy-Monkey Clean UI: Dark mode as default (e.g. dark background class)
    const body = page.locator('body');
    await expect(body).toHaveClass(/dark|bg-slate-900|bg-zinc-950|bg-black/);

    // 2. Locate VIN Ingestion components
    const vinInput = page.locator('[data-testid="vin-input"]');
    const scanButton = page.locator('[data-testid="scan-barcode-btn"]');

    await expect(vinInput).toBeVisible();
    await expect(scanButton).toBeVisible();

    // 3. Ensure touch target size of scan button is >= 48px height
    const scanBtnBoundingBox = await scanButton.boundingBox();
    expect(scanBtnBoundingBox).not.toBeNull();
    expect(scanBtnBoundingBox).toBeDefined();
    expect(Math.round(scanBtnBoundingBox!.height)).toBeGreaterThanOrEqual(48);

    // 4. Enter a valid VIN and submit
    await vinInput.fill('1HGBH41JXMN109186');
    const submitVinBtn = page.locator('[data-testid="submit-vin-btn"]');
    await expect(submitVinBtn).toBeVisible();
    
    const submitBtnBoundingBox = await submitVinBtn.boundingBox();
    expect(submitBtnBoundingBox).not.toBeNull();
    expect(submitBtnBoundingBox).toBeDefined();
    expect(Math.round(submitBtnBoundingBox!.height)).toBeGreaterThanOrEqual(48);

    await submitVinBtn.click();
    
    // Page transition to diagnostic input screen
    await expect(page).toHaveURL(/\/diagnose/);
  });

  test('Step 2: Diagnostic Input & Tool Constraint Profile Selection', async ({ page }) => {
    // Navigate directly to diagnose (simulate VIN already in context/state or passed in URL)
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('rapp_vin', '1HGBH41JXMN109186');
    });
    await page.goto('/diagnose');

    // 1. Check symptoms/OBD-II input presence
    const symptomsInput = page.locator('[data-testid="symptoms-input"]');
    await expect(symptomsInput).toBeVisible();
    await symptomsInput.fill('P0301 - Cylinder 1 Misfire Detected');

    // 2. Select Tool Constraints
    const toolHandTools = page.locator('[data-testid="tool-hand-tools"]');
    const toolJackStands = page.locator('[data-testid="tool-jack-stands"]');
    const toolMultimeter = page.locator('[data-testid="tool-multimeter"]');

    await expect(toolHandTools).toBeVisible();
    await expect(toolJackStands).toBeVisible();
    await expect(toolMultimeter).toBeVisible();

    // Check oversized targets for checkboxes/labels
    const labelHandTools = page.locator('label[for="tool-hand-tools"]');
    const labelBoundingBox = await labelHandTools.boundingBox();
    expect(labelBoundingBox).not.toBeNull();
    expect(labelBoundingBox).toBeDefined();
    expect(Math.round(labelBoundingBox!.height)).toBeGreaterThanOrEqual(48);

    await toolHandTools.check();
    await toolJackStands.check();

    // 3. Submit for diagnosis
    const submitDiagnoseBtn = page.locator('[data-testid="submit-diagnose-btn"]');
    await expect(submitDiagnoseBtn).toBeVisible();
    await submitDiagnoseBtn.click();

    // Redirected to results screen
    await expect(page).toHaveURL(/\/results/);
  });

  test('Step 3 & 4: Free Diagnosis, Paywall Gating & Stripe Verification', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('rapp_vin', '1HGBH41JXMN109186');
      localStorage.setItem('rapp_symptoms', 'P0301 - Cylinder 1 Misfire Detected');
    });
    await page.goto('/results');

    // 1. Verify Free Diagnosis summary is visible
    const freeSummary = page.locator('[data-testid="free-diagnosis-summary"]');
    await expect(freeSummary).toBeVisible();

    // 2. Verify detailed repair steps are locked/gated behind Stripe checkout CTA
    const repairStepsSection = page.locator('[data-testid="locked-repair-steps"]');
    const checkoutBtn = page.locator('[data-testid="payment-cta-btn"]');

    await expect(repairStepsSection).not.toBeVisible();
    await expect(checkoutBtn).toBeVisible();
    await expect(checkoutBtn).toContainText(/Unlock/i);

    // 3. Simulate Stripe Redirect success by accessing the success route
    // The Success handler stores {vin, stripeSessionId} in localStorage and routes back to repair/results
    await page.goto('/repair/success?session_id=cs_test_123&vin=1HGBH41JXMN109186');

    // Wait for the redirect to finish and local storage sync
    await page.waitForURL((url) => url.pathname === '/repair');

    // Verify localStorage contains the unlocked status
    const unlockedState = await page.evaluate(() => {
      return localStorage.getItem('rapp_unlocked_1HGBH41JXMN109186');
    });
    expect(unlockedState).not.toBeNull();

    // 4. Verify detailed repair steps with OEM citations are now fully visible
    const detailedSteps = page.locator('[data-testid="detailed-repair-steps"]');
    await expect(detailedSteps).toBeVisible();
    
    const citation = page.locator('[data-testid="rag-citation"]');
    await expect(citation).toBeVisible();
  });

  test('Safety Protocol: Non-dismissible Warning Banner for High-Risk Systems', async ({ page }) => {
    // Navigate to diagnose and input a high-risk symptom (e.g. Airbags or EV battery)
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('rapp_vin', '1HGBH41JXMN109186');
    });
    await page.goto('/diagnose');
    
    const symptomsInput = page.locator('[data-testid="symptoms-input"]');
    await symptomsInput.fill('Airbag warning light on, passenger side deployment fault');

    const submitDiagnoseBtn = page.locator('[data-testid="submit-diagnose-btn"]');
    await submitDiagnoseBtn.click();

    await page.waitForURL(/\/results/);

    // Verify safety warning is displayed and highly prominent
    const safetyBanner = page.locator('[data-testid="safety-warning-banner"]');
    await expect(safetyBanner).toBeVisible();
    await expect(safetyBanner).toContainText(/Airbag/i);
    await expect(safetyBanner).toHaveClass(/border-orange-500|bg-orange-950|text-orange-500/);

    // Ensure it is non-dismissible (does not contain a close button)
    const closeBtn = safetyBanner.locator('button, [role="button"], .close-btn');
    await expect(closeBtn).not.toBeVisible();
  });

  test('Step 5: Year/Make/Model Cascading Dropdowns & Submit', async ({ page }) => {
    await page.goto('/');

    const selectYear = page.locator('[data-testid="select-year"]');
    const selectMake = page.locator('[data-testid="select-make"]');
    const selectModel = page.locator('[data-testid="select-model"]');
    const submitYmmBtn = page.locator('[data-testid="submit-ymm-btn"]');

    // 1. Initial State: Year enabled, Make/Model disabled, Submit disabled
    await expect(selectYear).toBeEnabled();
    await expect(selectMake).toBeDisabled();
    await expect(selectModel).toBeDisabled();
    await expect(submitYmmBtn).toBeDisabled();

    // 2. Select Year: Unlocks Make dropdown
    await selectYear.selectOption('2023');
    await expect(selectMake).toBeEnabled();
    await expect(selectModel).toBeDisabled();
    await expect(submitYmmBtn).toBeDisabled();

    // 3. Select Make: Unlocks Model dropdown
    await selectMake.selectOption('HONDA');
    await expect(selectModel).toBeEnabled();
    await expect(submitYmmBtn).toBeDisabled();

    // 4. Select Model: Unlocks Submit button
    await selectModel.selectOption('ACCORD');
    await expect(submitYmmBtn).toBeEnabled();

    // 5. Submit YMM selector: Transitions to /diagnose and sets localStorage
    await submitYmmBtn.click();
    await page.waitForURL(/\/diagnose/);

    // Verify localStorage has correct synthetic VIN
    const storedVin = await page.evaluate(() => localStorage.getItem('rapp_vin'));
    expect(storedVin).toBe('SYN23HONDAACCORDX');
  });

  test('Step 6: Diagnose Page Back Button Navigation', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('rapp_vin', '1HGBH41JXMN109186');
    });
    await page.goto('/diagnose');

    const backBtn = page.locator('[data-testid="back-to-home-btn"]');
    await expect(backBtn).toBeVisible();

    await backBtn.click();
    await page.waitForURL(url => url.pathname === '/');
  });
});
