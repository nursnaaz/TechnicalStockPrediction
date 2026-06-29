import { test, expect } from '@playwright/test';

/**
 * "All Halal Stocks" preset loads the full universe (~212 tickers) into the input.
 * Hits the real /api/v1/halal-universe endpoint.
 */
test('All Halal Stocks button loads the full halal universe', async ({ page }) => {
  await page.goto('/');

  const allHalal = page.getByRole('button', { name: /All Halal Stocks/ });
  await expect(allHalal).toBeVisible();
  await allHalal.click();

  // Input fills with many comma-separated tickers; the button shows the count.
  const input = page.locator('input[placeholder*="ticker"]');
  await expect.poll(async () => (await input.inputValue()).split(',').filter(Boolean).length, {
    timeout: 15000,
  }).toBeGreaterThan(100);

  await expect(page.getByRole('button', { name: /All Halal Stocks \(\d+\)/ })).toBeVisible();

  await page.screenshot({ path: 'test-results/screenshots/v3-all-halal.png', fullPage: true });
});
