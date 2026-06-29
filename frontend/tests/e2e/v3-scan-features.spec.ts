import { test, expect } from '@playwright/test';

/**
 * V3 Live-Scanner enhancements: summary line, min-score filter, score breakdown popover,
 * and sortable results. Deterministic via route-mock.
 */
const sig = {
  price_above_sma50: true, price_above_ema20: true, macd_above_signal: true,
  macd_histogram_positive: true, volume_above_average: false, relative_strength_positive: true,
};

function ticker(t: string, score: number, price: number, bd: Record<string, number>) {
  return { ticker: t, bullish_score: score, signals: sig, current_price: price, indicators: {}, score_breakdown: bd };
}

test('summary line, min-score filter, breakdown popover and sorting', async ({ page }) => {
  await page.route('**/api/v1/scan', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        scan_id: 'feat-1',
        market_regime: 'bullish',
        score_threshold: 65,
        ranked_tickers: [
          ticker('AAA', 88, 150, { trend: 18, momentum: 18, strength: 16, confirmation: 20, stage_pattern: 16 }),
          ticker('BBB', 70, 40, { trend: 14, momentum: 12, strength: 14, confirmation: 20, stage_pattern: 10 }),
        ],
        metadata: { timestamp: new Date().toISOString(), ticker_count: 2, duration_seconds: 0.2 },
      }),
    });
  });

  await page.goto('/');
  await page.locator('input[placeholder*="ticker"]').fill('AAA, BBB');
  await page.locator('button:has-text("Run Scan")').click();

  // (4) Summary line
  const summary = page.getByTestId('scan-summary');
  await expect(summary).toBeVisible({ timeout: 15000 });
  await expect(summary).toContainText(/Showing 2 of 2/);
  await expect(summary).toContainText(/BUY ≥ 65/);

  // (2) Score breakdown popover
  await page.getByTestId('score-popover-trigger').first().click();
  await expect(page.getByText('Confirmation')).toBeVisible();
  await expect(page.getByText(/score 88/)).toBeVisible();
  await page.keyboard.press('Escape');

  // (3) Sort by Price ascending → BBB ($40) before AAA ($150)
  await page.getByRole('columnheader', { name: 'Price' }).click();
  const firstRow = page.locator('table tbody tr').first();
  await expect(firstRow).toContainText('BBB');

  // (1) Min-score filter → raise to 80, only AAA (88) remains
  const slider = page.locator('input[type="range"]').first();
  await slider.focus();
  for (let i = 0; i < 16; i++) await slider.press('ArrowRight'); // 0 -> 80
  await expect(page.getByTestId('scan-summary')).toContainText(/Showing 1 of 2/);
  await expect(page.locator('table')).not.toContainText('BBB');

  await page.screenshot({ path: 'test-results/screenshots/v3-scan-features.png', fullPage: true });
});
