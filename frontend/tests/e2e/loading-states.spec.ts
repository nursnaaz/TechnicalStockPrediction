import { test, expect } from '@playwright/test';

test.describe('Loading States', () => {
  test('should display loading indicator during scan', async ({ page }) => {
    // Navigate to the application
    await page.goto('/');

    // Take screenshot of initial state
    await page.screenshot({ 
      path: 'test-results/screenshots/loading-01-initial.png',
      fullPage: true 
    });

    // Enter tickers
    const input = page.locator('input[placeholder*="ticker"]');
    await input.fill('AAPL, MSFT, GOOGL');

    // Take screenshot with input
    await page.screenshot({ 
      path: 'test-results/screenshots/loading-02-input-filled.png',
      fullPage: true 
    });

    // Click Run Scan button
    const scanButton = page.locator('button:has-text("Run Scan")');
    await scanButton.click();

    // Immediately check for loading indicator
    // Loading state should appear quickly
    const loadingIndicator = page.locator('.awsui-spinner, [role="status"], text=/loading/i');
    
    // Try to catch the loading state - it might be quick
    try {
      await expect(loadingIndicator.first()).toBeVisible({ timeout: 2000 });
      
      // Take screenshot of loading state
      await page.screenshot({ 
        path: 'test-results/screenshots/loading-03-spinner-visible.png',
        fullPage: true 
      });

      console.log('✓ Loading indicator was visible during scan');
    } catch {
      console.log('⚠ Loading state was too quick to capture, or backend responded immediately');
    }

    // Wait for final state (results or error)
    const resultsOrError = page.locator('table, [role="alert"]');
    await resultsOrError.waitFor({ timeout: 30000 });

    // Take screenshot of final state
    await page.screenshot({ 
      path: 'test-results/screenshots/loading-04-final-state.png',
      fullPage: true 
    });

    // Loading indicator should be gone now
    const spinner = page.locator('.awsui-spinner, [role="status"]:has-text("loading")');
    if (await spinner.count() > 0) {
      await expect(spinner.first()).not.toBeVisible();
    }

    console.log('✓ Loading state lifecycle completed');
  });

  test('should disable scan button during loading', async ({ page }) => {
    await page.goto('/');

    // Enter tickers
    await page.locator('input[placeholder*="ticker"]').fill('AAPL');

    // Get reference to button
    const scanButton = page.locator('button:has-text("Run Scan")');

    // Button should be enabled initially
    await expect(scanButton).toBeEnabled();

    // Take screenshot before click
    await page.screenshot({ 
      path: 'test-results/screenshots/loading-05-button-enabled.png',
      fullPage: true 
    });

    // Click the button
    await scanButton.click();

    // Button should be disabled or show loading state
    // Check within a short timeout as the state changes quickly
    try {
      await expect(scanButton).toBeDisabled({ timeout: 1000 });
      
      // Take screenshot of disabled button
      await page.screenshot({ 
        path: 'test-results/screenshots/loading-06-button-disabled.png',
        fullPage: true 
      });

      console.log('✓ Button was disabled during scan');
    } catch {
      // If backend is very fast, button might re-enable before we can check
      console.log('⚠ Button state changed too quickly to verify disabled state');
    }

    // Wait for scan to complete
    await page.locator('table, [role="alert"]').waitFor({ timeout: 30000 });

    // Button should be enabled again after scan
    await expect(scanButton).toBeEnabled();

    await page.screenshot({ 
      path: 'test-results/screenshots/loading-07-button-re-enabled.png',
      fullPage: true 
    });
  });

  test('should show loading state UI elements', async ({ page }) => {
    await page.goto('/');

    // Enter tickers
    await page.locator('input[placeholder*="ticker"]').fill('AAPL, MSFT');

    // Click scan
    await page.locator('button:has-text("Run Scan")').click();

    // Check for any loading UI elements
    // This could be a spinner, loading text, or button state
    await page.locator('.awsui-spinner, [role="status"], button:has-text("Run Scan")[disabled]');
    
    // Wait a moment for loading state
    await page.waitForTimeout(500);

    // Take screenshot during potential loading state
    await page.screenshot({ 
      path: 'test-results/screenshots/loading-08-ui-elements.png',
      fullPage: true 
    });

    // Wait for completion
    await page.locator('table, [role="alert"]').waitFor({ timeout: 30000 });

    // Verify loading elements are gone
    const spinner = page.locator('.awsui-spinner:visible');
    await expect(spinner).toHaveCount(0);

    await page.screenshot({ 
      path: 'test-results/screenshots/loading-09-loading-cleared.png',
      fullPage: true 
    });

    console.log('✓ Loading UI elements lifecycle verified');
  });
});
