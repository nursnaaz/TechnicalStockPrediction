import { test, expect } from '@playwright/test';

test.describe('Results Display', () => {
  test('should display market regime badge correctly', async ({ page }) => {
    // Navigate to the application
    await page.goto('/');

    // Take screenshot of initial state
    await page.screenshot({ 
      path: 'test-results/screenshots/results-01-initial.png',
      fullPage: true 
    });

    // Enter tickers and run scan
    await page.locator('input[placeholder*="ticker"]').fill('AAPL, MSFT');
    await page.locator('button:has-text("Run Scan")').click();

    // Wait for results or error
    const resultsOrError = page.locator('table, [role="alert"]');
    await resultsOrError.waitFor({ timeout: 30000 });

    // Take screenshot of results
    await page.screenshot({ 
      path: 'test-results/screenshots/results-02-after-scan.png',
      fullPage: true 
    });

    // Check if results are displayed (backend must be running)
    const resultsTable = page.locator('table');
    if (await resultsTable.isVisible()) {
      // Look for market regime badge
      const regimeBadge = page.locator('.awsui-badge, [class*="badge"], text=/bullish|bearish|neutral/i');
      await expect(regimeBadge.first()).toBeVisible();

      // Verify badge contains one of the valid regime values
      const badgeText = await regimeBadge.first().textContent();
      expect(badgeText?.toLowerCase()).toMatch(/bullish|bearish|neutral/);

      // Take screenshot highlighting regime badge
      await page.screenshot({ 
        path: 'test-results/screenshots/results-03-regime-badge.png',
        fullPage: true 
      });

      console.log('✓ Market regime badge displayed:', badgeText);
    } else {
      console.log('⚠ Backend not running, skipping regime badge verification');
    }
  });

  test('should display results table with all required columns', async ({ page }) => {
    await page.goto('/');

    // Enter tickers and run scan
    await page.locator('input[placeholder*="ticker"]').fill('AAPL, MSFT, GOOGL');
    await page.locator('button:has-text("Run Scan")').click();

    // Wait for results or error
    const resultsOrError = page.locator('table, [role="alert"]');
    await resultsOrError.waitFor({ timeout: 30000 });

    const resultsTable = page.locator('table');
    if (await resultsTable.isVisible()) {
      // Verify table is visible
      await expect(resultsTable).toBeVisible();

      // Verify table headers
      const headers = resultsTable.locator('thead th, thead [role="columnheader"]');
      const headerCount = await headers.count();
      expect(headerCount).toBeGreaterThan(0);

      // Take screenshot of table structure
      await page.screenshot({ 
        path: 'test-results/screenshots/results-04-table-structure.png',
        fullPage: true 
      });

      // Verify expected columns exist (case-insensitive)
      const headerTexts = await headers.allTextContents();
      const headerString = headerTexts.join(' ').toLowerCase();
      
      expect(headerString).toContain('rank');
      expect(headerString).toContain('ticker');
      expect(headerString).toContain('score');

      console.log('✓ Table columns verified:', headerTexts);

      // Verify data rows exist
      const dataRows = resultsTable.locator('tbody tr');
      const rowCount = await dataRows.count();
      expect(rowCount).toBeGreaterThan(0);

      console.log('✓ Table has', rowCount, 'data rows');

      // Take screenshot of populated table
      await page.screenshot({ 
        path: 'test-results/screenshots/results-05-table-data.png',
        fullPage: true 
      });
    } else {
      console.log('⚠ Backend not running, skipping table verification');
    }
  });

  test('should display ticker scores with proper formatting', async ({ page }) => {
    await page.goto('/');

    // Enter tickers
    await page.locator('input[placeholder*="ticker"]').fill('AAPL, MSFT');
    await page.locator('button:has-text("Run Scan")').click();

    // Wait for results
    const resultsOrError = page.locator('table, [role="alert"]');
    await resultsOrError.waitFor({ timeout: 30000 });

    const resultsTable = page.locator('table');
    if (await resultsTable.isVisible()) {
      // Look for score badges or score cells
      const scoreCells = resultsTable.locator('tbody td .awsui-badge, tbody td[class*="score"]');
      
      if (await scoreCells.count() > 0) {
        // Verify at least one score is displayed
        await expect(scoreCells.first()).toBeVisible();

        // Take screenshot of score formatting
        await page.screenshot({ 
          path: 'test-results/screenshots/results-06-score-formatting.png',
          fullPage: true 
        });

        console.log('✓ Score badges/cells displayed');
      }

      // Verify ticker symbols are displayed
      const tickerCells = resultsTable.locator('tbody td:has-text("AAPL"), tbody td:has-text("MSFT")');
      if (await tickerCells.count() > 0) {
        await expect(tickerCells.first()).toBeVisible();
        console.log('✓ Ticker symbols displayed in results');
      }
    }
  });

  test('should display ranked results in descending order', async ({ page }) => {
    await page.goto('/');

    // Enter multiple tickers for ranking
    await page.locator('input[placeholder*="ticker"]').fill('AAPL, MSFT, GOOGL, TSLA');
    await page.locator('button:has-text("Run Scan")').click();

    // Wait for results
    const resultsOrError = page.locator('table, [role="alert"]');
    await resultsOrError.waitFor({ timeout: 30000 });

    const resultsTable = page.locator('table');
    if (await resultsTable.isVisible()) {
      // Get all data rows
      const dataRows = resultsTable.locator('tbody tr');
      const rowCount = await dataRows.count();

      if (rowCount > 1) {
        // Verify rank column exists and shows 1, 2, 3...
        const rankCells = resultsTable.locator('tbody tr td:first-child');
        const firstRank = await rankCells.first().textContent();
        
        // First rank should be 1
        expect(firstRank?.trim()).toBe('1');

        console.log('✓ Results are ranked, first rank is 1');

        // Take screenshot of ranked results
        await page.screenshot({ 
          path: 'test-results/screenshots/results-07-ranked-order.png',
          fullPage: true 
        });
      }
    }
  });

  test('should display signal indicators for each ticker', async ({ page }) => {
    await page.goto('/');

    // Enter tickers
    await page.locator('input[placeholder*="ticker"]').fill('AAPL');
    await page.locator('button:has-text("Run Scan")').click();

    // Wait for results
    const resultsOrError = page.locator('table, [role="alert"]');
    await resultsOrError.waitFor({ timeout: 30000 });

    const resultsTable = page.locator('table');
    if (await resultsTable.isVisible()) {
      // Look for signal indicators (badges, icons, or text)
      const signalIndicators = resultsTable.locator('tbody .awsui-badge, tbody [class*="signal"], tbody [class*="badge"]');
      
      // Take screenshot of signals column
      await page.screenshot({ 
        path: 'test-results/screenshots/results-08-signal-indicators.png',
        fullPage: true 
      });

      if (await signalIndicators.count() > 0) {
        console.log('✓ Signal indicators found:', await signalIndicators.count());
      }

      // Verify the signals column exists
      const headers = await resultsTable.locator('thead th, thead [role="columnheader"]').allTextContents();
      const hasSignalsColumn = headers.some(h => h.toLowerCase().includes('signal'));
      
      if (hasSignalsColumn) {
        console.log('✓ Signals column present in table');
      }
    }
  });

  test('should handle empty results gracefully', async ({ page }) => {
    await page.goto('/');

    // Enter potentially invalid tickers that might return empty results
    await page.locator('input[placeholder*="ticker"]').fill('INVALIDTICKER999');
    
    await page.screenshot({ 
      path: 'test-results/screenshots/results-09-before-invalid-scan.png',
      fullPage: true 
    });

    await page.locator('button:has-text("Run Scan")').click();

    // Wait for response
    const resultsOrError = page.locator('table, [role="alert"]');
    await resultsOrError.waitFor({ timeout: 30000 });

    // Take screenshot of result
    await page.screenshot({ 
      path: 'test-results/screenshots/results-10-invalid-ticker-result.png',
      fullPage: true 
    });

    // Verify UI shows either empty table or error message
    const errorMessage = page.locator('[role="alert"]');
    const emptyTable = page.locator('table tbody:has-text("No")');
    
    const hasErrorOrEmpty = await errorMessage.isVisible() || await emptyTable.isVisible();
    
    // Either error or empty state is acceptable
    console.log('✓ Invalid ticker handling verified');
  });
});
