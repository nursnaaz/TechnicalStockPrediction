import { test, expect } from '@playwright/test';

/**
 * The Live Scanner "Download Report" button downloads an HTML report of the results.
 */
const sig = {
  price_above_sma50: true, price_above_ema20: true, macd_above_signal: true,
  macd_histogram_positive: true, volume_above_average: false, relative_strength_positive: true,
};

test('Download Report button downloads an HTML scan report', async ({ page }) => {
  await page.route('**/api/v1/scan', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        scan_id: 'dl-1',
        market_regime: 'bullish',
        score_threshold: 65,
        ranked_tickers: [
          {
            ticker: 'AAA', bullish_score: 86, signals: sig, current_price: 150, indicators: {},
            score_breakdown: { trend: 18, momentum: 18, strength: 16, confirmation: 20, stage_pattern: 14 },
          },
        ],
        metadata: { timestamp: new Date().toISOString(), ticker_count: 1, duration_seconds: 0.2 },
      }),
    });
  });

  await page.goto('/');
  await page.locator('input[placeholder*="ticker"]').fill('AAA');
  await page.locator('button:has-text("Run Scan")').click();

  const button = page.getByTestId('download-scan-report');
  await expect(button).toBeVisible({ timeout: 15000 });

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    button.click(),
  ]);

  expect(download.suggestedFilename()).toMatch(/^scan-report-\d{4}-\d{2}-\d{2}\.html$/);

  // Verify the downloaded HTML actually contains the scan data.
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const c of stream) chunks.push(c as Buffer);
  const html = Buffer.concat(chunks).toString('utf-8');
  expect(html).toContain('Bullish Stock Scan Report');
  expect(html).toContain('AAA');
  expect(html).toContain('BULLISH');
  expect(html).toContain('86');
});
