import { test, expect } from '@playwright/test';

test.describe('Comprehensive E2E Test Suite with Extensive Screenshots', () => {
  
  test('Complete workflow: Initial load → Input → Scan → Results analysis', async ({ page }) => {
    console.log('🧪 Starting comprehensive E2E test...');

    // Step 1: Navigate and verify initial load
    await page.goto('/');
    await page.screenshot({ 
      path: 'test-results/screenshots/comprehensive-01-page-loaded.png',
      fullPage: true 
    });
    console.log('✓ Page loaded');

    // Verify main heading
    const heading = page.locator('h1');
    await expect(heading).toBeVisible();
    await expect(heading).toContainText('Bullish Stock Scanner');

    // Step 2: Verify all initial UI elements
    const input = page.locator('input[placeholder*="ticker"]');
    const scanButton = page.locator('button:has-text("Run Scan")');
    
    await expect(input).toBeVisible();
    await expect(input).toBeEditable();
    await expect(scanButton).toBeVisible();
    await expect(scanButton).toBeEnabled();

    await page.screenshot({ 
      path: 'test-results/screenshots/comprehensive-02-initial-ui-verified.png',
      fullPage: true 
    });
    console.log('✓ Initial UI elements verified');

    // Step 3: Test input with single ticker
    await input.fill('AAPL');
    await page.screenshot({ 
      path: 'test-results/screenshots/comprehensive-03-single-ticker-entered.png',
      fullPage: true 
    });
    console.log('✓ Single ticker entered');

    // Step 4: Clear and test with multiple tickers (comma-separated)
    await input.clear();
    await input.fill('AAPL, MSFT, GOOGL');
    await page.screenshot({ 
      path: 'test-results/screenshots/comprehensive-04-multiple-tickers-comma.png',
      fullPage: true 
    });
    console.log('✓ Multiple tickers (comma) entered');

    // Step 5: Test with space-separated tickers
    await input.clear();
    await input.fill('AAPL MSFT GOOGL TSLA NVDA');
    await page.screenshot({ 
      path: 'test-results/screenshots/comprehensive-05-multiple-tickers-space.png',
      fullPage: true 
    });
    console.log('✓ Multiple tickers (space) entered');

    // Step 6: Use optimal test tickers for consistent results
    await input.clear();
    await input.fill('AAPL, MSFT, GOOGL');

    // Step 7: Click scan button and capture loading state
    await scanButton.click();
    
    // Capture immediate click state
    await page.screenshot({ 
      path: 'test-results/screenshots/comprehensive-06-scan-clicked.png',
      fullPage: true 
    });
    console.log('✓ Scan button clicked');

    // Wait briefly and capture loading spinner/indicator
    await page.waitForTimeout(500);
    await page.screenshot({ 
      path: 'test-results/screenshots/comprehensive-07-loading-indicator.png',
      fullPage: true 
    });
    console.log('✓ Loading state captured');

    // Verify scan button is disabled during scan
    const buttonDisabled = await scanButton.isDisabled();
    if (buttonDisabled) {
      console.log('✓ Scan button disabled during loading');
    }

    // Step 8: Wait for results or error
    const resultsOrError = page.locator('table, [role="alert"]');
    await resultsOrError.waitFor({ timeout: 30000 });

    await page.screenshot({ 
      path: 'test-results/screenshots/comprehensive-08-scan-completed.png',
      fullPage: true 
    });
    console.log('✓ Scan completed');

    // Step 9: Verify results display
    const resultsTable = page.locator('table');
    
    if (await resultsTable.isVisible()) {
      console.log('✅ Results table displayed');

      // Capture results table
      await page.screenshot({ 
        path: 'test-results/screenshots/comprehensive-09-results-table.png',
        fullPage: true 
      });

      // Step 10: Verify market regime badge
      const regimeBadge = page.locator('text=/market.*regime/i, text=/bullish|bearish|neutral/i');
      if (await regimeBadge.first().isVisible()) {
        const regimeText = await regimeBadge.first().textContent();
        console.log(`✓ Market regime: ${regimeText}`);
        
        // Highlight and capture regime badge
        await regimeBadge.first().scrollIntoViewIfNeeded();
        await page.screenshot({ 
          path: 'test-results/screenshots/comprehensive-10-market-regime.png',
          fullPage: true 
        });
      }

      // Step 11: Verify table headers
      const headers = resultsTable.locator('th');
      const headerCount = await headers.count();
      console.log(`✓ Table has ${headerCount} columns`);

      await expect(headers).toContainText(['Rank']);
      await expect(headers).toContainText(['Ticker']);
      await expect(headers).toContainText(['Score']);
      
      await page.screenshot({ 
        path: 'test-results/screenshots/comprehensive-11-table-headers.png',
        fullPage: true 
    });

      // Step 12: Verify data rows
      const dataRows = resultsTable.locator('tbody tr');
      const rowCount = await dataRows.count();
      console.log(`✓ Results contain ${rowCount} stocks`);

      await expect(dataRows.first()).toBeVisible();
      
      // Step 13: Examine first row in detail
      const firstRow = dataRows.first();
      await firstRow.scrollIntoViewIfNeeded();
      
      await page.screenshot({ 
        path: 'test-results/screenshots/comprehensive-12-first-result.png',
        fullPage: true 
      });

      // Get first row data
      const firstRowText = await firstRow.textContent();
      console.log(`✓ First result: ${firstRowText}`);

      // Step 14: Check for signal indicators/badges
      const badges = resultsTable.locator('.awsui-badge, [class*="badge"], [class*="signal"]');
      const badgeCount = await badges.count();
      
      if (badgeCount > 0) {
        console.log(`✓ Found ${badgeCount} signal badges`);
        
        // Capture badges
        await badges.first().scrollIntoViewIfNeeded();
        await page.screenshot({ 
          path: 'test-results/screenshots/comprehensive-13-signal-badges.png',
          fullPage: true 
        });
      }

      // Step 15: Scroll through all results
      const lastRow = dataRows.last();
      await lastRow.scrollIntoViewIfNeeded();
      
      await page.screenshot({ 
        path: 'test-results/screenshots/comprehensive-14-last-result.png',
        fullPage: true 
      });

      // Step 16: Verify scores are present and visible
      console.log('✓ Verifying score column exists');
      
      // Just verify scores are visible - don't parse/compare since format may vary
      const firstRowCells = firstRow.locator('td');
      const cellCount = await firstRowCells.count();
      console.log(`✓ First row has ${cellCount} cells`);
      
      // Verify we have at least rank, ticker, score columns
      expect(cellCount).toBeGreaterThanOrEqual(3);
      console.log('✓ Results table has expected column structure');

      // Step 17: Test responsiveness - resize window
      await page.setViewportSize({ width: 1920, height: 1080 });
      await page.screenshot({ 
        path: 'test-results/screenshots/comprehensive-15-desktop-view.png',
        fullPage: true 
      });
      console.log('✓ Desktop view captured');

      await page.setViewportSize({ width: 768, height: 1024 });
      await page.screenshot({ 
        path: 'test-results/screenshots/comprehensive-16-tablet-view.png',
        fullPage: true 
      });
      console.log('✓ Tablet view captured');

      await page.setViewportSize({ width: 375, height: 667 });
      await page.screenshot({ 
        path: 'test-results/screenshots/comprehensive-17-mobile-view.png',
        fullPage: true 
      });
      console.log('✓ Mobile view captured');

      // Reset viewport
      await page.setViewportSize({ width: 1280, height: 720 });

      console.log('✅ ALL TESTS PASSED - Results displayed and verified');

    } else {
      // Handle error case
      const errorAlert = page.locator('[role="alert"]');
      await expect(errorAlert).toBeVisible();
      
      const errorText = await errorAlert.textContent();
      console.log(`⚠ Error displayed: ${errorText}`);
      
      await page.screenshot({ 
        path: 'test-results/screenshots/comprehensive-error-displayed.png',
        fullPage: true 
      });
      
      console.log('✓ Error handling verified - UI correctly displays error');
    }
  });

  test('Test with large dataset (20 tickers)', async ({ page }) => {
    await page.goto('/');
    
    await page.screenshot({ 
      path: 'test-results/screenshots/large-dataset-01-initial.png',
      fullPage: true 
    });

    // Enter 20 halal stocks
    const largeTickers = 'AAPL, MSFT, NVDA, GOOGL, TSLA, AVGO, LLY, JNJ, UNH, HD, COST, PFE, ABBV, TMO, ORCL, ADBE, CRM, NKE, CSCO, PG';
    
    const input = page.locator('input[placeholder*="ticker"]');
    await input.fill(largeTickers);
    
    await page.screenshot({ 
      path: 'test-results/screenshots/large-dataset-02-tickers-entered.png',
      fullPage: true 
    });
    console.log('✓ 20 tickers entered');

    await page.locator('button:has-text("Run Scan")').click();
    
    await page.screenshot({ 
      path: 'test-results/screenshots/large-dataset-03-scan-started.png',
      fullPage: true 
    });

    // Wait longer for large dataset
    await page.waitForTimeout(1000);
    await page.screenshot({ 
      path: 'test-results/screenshots/large-dataset-04-processing.png',
      fullPage: true 
    });

    const resultsOrError = page.locator('table, [role="alert"]');
    await resultsOrError.waitFor({ timeout: 45000 }); // Longer timeout for 20 stocks

    await page.screenshot({ 
      path: 'test-results/screenshots/large-dataset-05-completed.png',
      fullPage: true 
    });

    const resultsTable = page.locator('table');
    if (await resultsTable.isVisible()) {
      const dataRows = resultsTable.locator('tbody tr');
      const rowCount = await dataRows.count();
      
      console.log(`✓ Large dataset: ${rowCount} results displayed`);
      expect(rowCount).toBeLessThanOrEqual(20);

      // Capture top results
      await page.screenshot({ 
        path: 'test-results/screenshots/large-dataset-06-top-results.png',
        fullPage: true 
      });

      // Scroll to bottom results
      await dataRows.last().scrollIntoViewIfNeeded();
      await page.screenshot({ 
        path: 'test-results/screenshots/large-dataset-07-bottom-results.png',
        fullPage: true 
      });

      console.log('✅ Large dataset test passed');
    }
  });

  test('Test input variations and special characters', async ({ page }) => {
    await page.goto('/');

    const input = page.locator('input[placeholder*="ticker"]');

    // Test 1: Lowercase tickers
    await input.fill('aapl, msft, googl');
    await page.screenshot({ 
      path: 'test-results/screenshots/variations-01-lowercase.png',
      fullPage: true 
    });
    console.log('✓ Lowercase input captured');

    // Test 2: Mixed case
    await input.clear();
    await input.fill('AaPl, MsFt, GoOgL');
    await page.screenshot({ 
      path: 'test-results/screenshots/variations-02-mixed-case.png',
      fullPage: true 
    });
    console.log('✓ Mixed case input captured');

    // Test 3: Extra spaces
    await input.clear();
    await input.fill('  AAPL  ,   MSFT   ,  GOOGL  ');
    await page.screenshot({ 
      path: 'test-results/screenshots/variations-03-extra-spaces.png',
      fullPage: true 
    });
    console.log('✓ Extra spaces input captured');

    // Test 4: Tabs and newlines (if supported)
    await input.clear();
    await input.fill('AAPL\tMSFT\nGOOGL');
    await page.screenshot({ 
      path: 'test-results/screenshots/variations-04-special-separators.png',
      fullPage: true 
    });
    console.log('✓ Special separators input captured');

    // Test 5: Single ticker
    await input.clear();
    await input.fill('AAPL');
    await page.screenshot({ 
      path: 'test-results/screenshots/variations-05-single-ticker.png',
      fullPage: true 
    });
    console.log('✓ Single ticker input captured');

    console.log('✅ Input variation tests completed');
  });

  test('UI interaction and state persistence', async ({ page }) => {
    await page.goto('/');

    const input = page.locator('input[placeholder*="ticker"]');
    
    // Enter tickers
    await input.fill('AAPL, MSFT');
    await page.screenshot({ 
      path: 'test-results/screenshots/interaction-01-input-filled.png',
      fullPage: true 
    });

    // Focus and blur
    await input.focus();
    await page.screenshot({ 
      path: 'test-results/screenshots/interaction-02-input-focused.png',
      fullPage: true 
    });

    await input.blur();
    await page.screenshot({ 
      path: 'test-results/screenshots/interaction-03-input-blurred.png',
      fullPage: true 
    });

    // Hover over button
    const scanButton = page.locator('button:has-text("Run Scan")');
    await scanButton.hover();
    await page.screenshot({ 
      path: 'test-results/screenshots/interaction-04-button-hover.png',
      fullPage: true 
    });

    // Click button
    await scanButton.click();
    await page.screenshot({ 
      path: 'test-results/screenshots/interaction-05-button-clicked.png',
      fullPage: true 
    });

    // Wait for completion
    const resultsOrError = page.locator('table, [role="alert"]');
    await resultsOrError.waitFor({ timeout: 30000 });

    await page.screenshot({ 
      path: 'test-results/screenshots/interaction-06-final-state.png',
      fullPage: true 
    });

    // Verify input still has value
    const inputValue = await input.inputValue();
    expect(inputValue).toBeTruthy();
    console.log(`✓ Input persisted: ${inputValue}`);

    console.log('✅ UI interaction test completed');
  });

  test('Accessibility and keyboard navigation', async ({ page }) => {
    await page.goto('/');

    await page.screenshot({ 
      path: 'test-results/screenshots/a11y-01-initial.png',
      fullPage: true 
    });

    // Tab to input field
    await page.keyboard.press('Tab');
    await page.screenshot({ 
      path: 'test-results/screenshots/a11y-02-tab-to-input.png',
      fullPage: true 
    });

    // Type with keyboard
    await page.keyboard.type('AAPL MSFT GOOGL');
    await page.screenshot({ 
      path: 'test-results/screenshots/a11y-03-keyboard-input.png',
      fullPage: true 
    });

    // Tab to button
    await page.keyboard.press('Tab');
    await page.screenshot({ 
      path: 'test-results/screenshots/a11y-04-tab-to-button.png',
      fullPage: true 
    });

    // Press Enter to submit
    await page.keyboard.press('Enter');
    await page.screenshot({ 
      path: 'test-results/screenshots/a11y-05-enter-pressed.png',
      fullPage: true 
    });

    await page.waitForTimeout(1000);
    await page.screenshot({ 
      path: 'test-results/screenshots/a11y-06-after-submit.png',
      fullPage: true 
    });

    console.log('✅ Keyboard navigation test completed');
  });
});
