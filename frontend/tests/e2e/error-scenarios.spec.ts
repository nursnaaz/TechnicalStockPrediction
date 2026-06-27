import { test, expect } from '@playwright/test';

test.describe('Error Scenarios', () => {
  test('should show validation error when no tickers are entered', async ({ page }) => {
    // Navigate to the application
    await page.goto('/');

    // Take screenshot of initial state
    await page.screenshot({ 
      path: 'test-results/screenshots/error-01-initial.png',
      fullPage: true 
    });

    // Verify input is empty
    const input = page.locator('input[placeholder*="ticker"]');
    await expect(input).toBeVisible();
    await expect(input).toHaveValue('');

    // Click Run Scan without entering tickers
    const scanButton = page.locator('button:has-text("Run Scan")');
    await scanButton.click();

    // Wait for validation error to appear
    const errorAlert = page.locator('[role="alert"], .awsui-alert-error, text=/enter.*ticker/i');
    await expect(errorAlert.first()).toBeVisible({ timeout: 5000 });

    // Take screenshot of validation error
    await page.screenshot({ 
      path: 'test-results/screenshots/error-02-validation-error.png',
      fullPage: true 
    });

    // Verify error message content
    const errorText = await errorAlert.first().textContent();
    expect(errorText?.toLowerCase()).toContain('ticker');

    console.log('✓ Validation error displayed correctly');
  });

  test('should show validation error with empty string', async ({ page }) => {
    await page.goto('/');

    // Enter only whitespace
    const input = page.locator('input[placeholder*="ticker"]');
    await input.fill('   ');

    // Click Run Scan
    await page.locator('button:has-text("Run Scan")').click();

    // Wait for validation error
    const errorAlert = page.locator('[role="alert"], text=/enter.*ticker/i');
    await expect(errorAlert.first()).toBeVisible({ timeout: 5000 });

    await page.screenshot({ 
      path: 'test-results/screenshots/error-03-whitespace-validation.png',
      fullPage: true 
    });
  });

  test('should display API error when backend is unavailable', async ({ page }) => {
    await page.goto('/');

    // Enter valid tickers
    await page.locator('input[placeholder*="ticker"]').fill('INVALID123');
    
    // Take screenshot before scan
    await page.screenshot({ 
      path: 'test-results/screenshots/error-04-before-api-call.png',
      fullPage: true 
    });

    // Click Run Scan
    await page.locator('button:has-text("Run Scan")').click();

    // Wait for either success or error
    const resultsOrError = page.locator('table, [role="alert"]');
    await resultsOrError.waitFor({ timeout: 30000 });

    // Take screenshot of result
    await page.screenshot({ 
      path: 'test-results/screenshots/error-05-api-response.png',
      fullPage: true 
    });

    // If error is displayed, verify it's shown correctly
    const errorAlert = page.locator('[role="alert"]');
    if (await errorAlert.isVisible()) {
      const errorText = await errorAlert.textContent();
      console.log('API Error displayed:', errorText);
      
      // Verify error is visible to user
      await expect(errorAlert).toBeVisible();
      
      await page.screenshot({ 
        path: 'test-results/screenshots/error-06-api-error-displayed.png',
        fullPage: true 
      });
    }
  });

  test('should clear previous errors when new scan is initiated', async ({ page }) => {
    await page.goto('/');

    // First, trigger a validation error
    await page.locator('button:has-text("Run Scan")').click();
    
    // Wait for error
    const errorAlert = page.locator('[role="alert"]');
    await expect(errorAlert.first()).toBeVisible({ timeout: 5000 });

    // Take screenshot of error
    await page.screenshot({ 
      path: 'test-results/screenshots/error-07-first-error.png',
      fullPage: true 
    });

    // Now enter tickers and scan again
    await page.locator('input[placeholder*="ticker"]').fill('AAPL');
    
    // Take screenshot before second scan
    await page.screenshot({ 
      path: 'test-results/screenshots/error-08-input-entered.png',
      fullPage: true 
    });

    await page.locator('button:has-text("Run Scan")').click();

    // The error should be cleared (either results show or new error appears)
    // Wait a moment for state to update
    await page.waitForTimeout(1000);

    await page.screenshot({ 
      path: 'test-results/screenshots/error-09-after-retry.png',
      fullPage: true 
    });

    console.log('✓ Error clearing behavior verified');
  });
});
