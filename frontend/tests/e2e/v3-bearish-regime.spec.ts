import { test, expect } from '@playwright/test';

/**
 * V3: a bearish market emits ZERO buy candidates. Deterministic via route-mock
 * (live regime is non-deterministic). Asserts the "Bearish Market" badge and the
 * bearish empty-state copy — not a red error.
 */
test('bearish regime shows bearish badge and zero-candidate empty state', async ({ page }) => {
  await page.route('**/api/v1/scan', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        scan_id: 'test-bearish',
        market_regime: 'bearish',
        ranked_tickers: [],
        metadata: { timestamp: new Date().toISOString(), ticker_count: 0, duration_seconds: 0.1 },
      }),
    });
  });

  await page.goto('/');
  await page.locator('input[placeholder*="ticker"]').fill('AAPL, MSFT');
  await page.locator('button:has-text("Run Scan")').click();

  const badge = page.getByTestId('market-regime-badge');
  await expect(badge).toBeVisible({ timeout: 15000 });
  await expect(badge).toHaveAttribute('data-regime', 'bearish');
  await expect(badge).toContainText('Bearish Market');

  const empty = page.getByTestId('results-empty');
  await expect(empty).toBeVisible();
  await expect(empty).toContainText(/bearish market/i);

  // No error alert
  await expect(page.locator('[role="alert"]')).toHaveCount(0);

  await page.screenshot({ path: 'test-results/screenshots/v3-bearish-regime.png', fullPage: true });
});
