import { test, expect } from '@playwright/test';

/**
 * V3 control: a bearish backtest date produces zero trades (no BUY signals).
 * Reworded from "0 BUY signals" to the actual UI concept: the backtest "no trades"
 * empty state. Deterministic via route-mock with a bearish, empty-trades response.
 */
test('bearish backtest date renders the no-trades empty state (zero signals)', async ({ page }) => {
  await page.route('**/api/v1/backtest/single', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        backtest_id: 'bt-bear', status: 'completed', as_of_date: '2026-03-01',
        horizon_days: 30, scan_id: 's-bear', market_regime: 'bearish',
        total_candidates: 0, trades_analyzed: 0, trades: [], metrics: {},
      }),
    });
  });

  await page.goto('/');
  await page.getByRole('tab', { name: 'Backtest' }).click();
  const dateInput = page.locator('input[placeholder="YYYY-MM-DD"]');
  await dateInput.click();
  await dateInput.pressSequentially('2026/03/01', { delay: 20 });
  await page.keyboard.press('Escape');
  await page.locator('input[placeholder*="AAPL"]').fill('AAPL, MSFT, NVDA');
  await page.getByRole('button', { name: 'Run', exact: true }).click();

  const empty = page.getByTestId('backtest-empty');
  await expect(empty).toBeVisible({ timeout: 15000 });
  await expect(empty).toContainText(/no trades/i);

  // No confusion matrix is rendered when there are zero trades
  await expect(page.getByTestId('cm-tp')).toHaveCount(0);

  await page.screenshot({ path: 'test-results/screenshots/v3-march-2026.png', fullPage: true });
});
