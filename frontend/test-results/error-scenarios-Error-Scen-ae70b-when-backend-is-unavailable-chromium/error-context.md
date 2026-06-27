# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: error-scenarios.spec.ts >> Error Scenarios >> should display API error when backend is unavailable
- Location: tests/e2e/error-scenarios.spec.ts:60:3

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.waitFor: Test timeout of 30000ms exceeded.
Call log:
  - waiting for locator('table, [role="alert"]') to be visible

```

# Page snapshot

```yaml
- main [ref=e4]:
  - generic [ref=e8]:
    - generic [ref=e11]:
      - heading "Bullish Stock Scanner" [level=1] [ref=e14]
      - paragraph [ref=e15]: Analyze technical indicators to identify potentially bullish stocks
    - generic [ref=e17]:
      - generic [ref=e23]:
        - textbox "Enter ticker symbols (e.g., AAPL, MSFT, GOOGL)" [ref=e26]: INVALID123
        - button "Run Scan" [ref=e28] [cursor=pointer]
      - generic [ref=e32]:
        - group [ref=e34]:
          - generic [ref=e36]:
            - img
          - generic [ref=e38]: All tickers failed to process. Please check ticker symbols and try again.
        - button [ref=e40] [cursor=pointer]:
          - generic [ref=e41]:
            - img
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('Error Scenarios', () => {
  4   |   test('should show validation error when no tickers are entered', async ({ page }) => {
  5   |     // Navigate to the application
  6   |     await page.goto('/');
  7   | 
  8   |     // Take screenshot of initial state
  9   |     await page.screenshot({ 
  10  |       path: 'test-results/screenshots/error-01-initial.png',
  11  |       fullPage: true 
  12  |     });
  13  | 
  14  |     // Verify input is empty
  15  |     const input = page.locator('input[placeholder*="ticker"]');
  16  |     await expect(input).toBeVisible();
  17  |     await expect(input).toHaveValue('');
  18  | 
  19  |     // Click Run Scan without entering tickers
  20  |     const scanButton = page.locator('button:has-text("Run Scan")');
  21  |     await scanButton.click();
  22  | 
  23  |     // Wait for validation error to appear
  24  |     const errorAlert = page.locator('[role="alert"], .awsui-alert-error, text=/enter.*ticker/i');
  25  |     await expect(errorAlert.first()).toBeVisible({ timeout: 5000 });
  26  | 
  27  |     // Take screenshot of validation error
  28  |     await page.screenshot({ 
  29  |       path: 'test-results/screenshots/error-02-validation-error.png',
  30  |       fullPage: true 
  31  |     });
  32  | 
  33  |     // Verify error message content
  34  |     const errorText = await errorAlert.first().textContent();
  35  |     expect(errorText?.toLowerCase()).toContain('ticker');
  36  | 
  37  |     console.log('✓ Validation error displayed correctly');
  38  |   });
  39  | 
  40  |   test('should show validation error with empty string', async ({ page }) => {
  41  |     await page.goto('/');
  42  | 
  43  |     // Enter only whitespace
  44  |     const input = page.locator('input[placeholder*="ticker"]');
  45  |     await input.fill('   ');
  46  | 
  47  |     // Click Run Scan
  48  |     await page.locator('button:has-text("Run Scan")').click();
  49  | 
  50  |     // Wait for validation error
  51  |     const errorAlert = page.locator('[role="alert"], text=/enter.*ticker/i');
  52  |     await expect(errorAlert.first()).toBeVisible({ timeout: 5000 });
  53  | 
  54  |     await page.screenshot({ 
  55  |       path: 'test-results/screenshots/error-03-whitespace-validation.png',
  56  |       fullPage: true 
  57  |     });
  58  |   });
  59  | 
  60  |   test('should display API error when backend is unavailable', async ({ page }) => {
  61  |     await page.goto('/');
  62  | 
  63  |     // Enter valid tickers
  64  |     await page.locator('input[placeholder*="ticker"]').fill('INVALID123');
  65  |     
  66  |     // Take screenshot before scan
  67  |     await page.screenshot({ 
  68  |       path: 'test-results/screenshots/error-04-before-api-call.png',
  69  |       fullPage: true 
  70  |     });
  71  | 
  72  |     // Click Run Scan
  73  |     await page.locator('button:has-text("Run Scan")').click();
  74  | 
  75  |     // Wait for either success or error
  76  |     const resultsOrError = page.locator('table, [role="alert"]');
> 77  |     await resultsOrError.waitFor({ timeout: 30000 });
      |                          ^ Error: locator.waitFor: Test timeout of 30000ms exceeded.
  78  | 
  79  |     // Take screenshot of result
  80  |     await page.screenshot({ 
  81  |       path: 'test-results/screenshots/error-05-api-response.png',
  82  |       fullPage: true 
  83  |     });
  84  | 
  85  |     // If error is displayed, verify it's shown correctly
  86  |     const errorAlert = page.locator('[role="alert"]');
  87  |     if (await errorAlert.isVisible()) {
  88  |       const errorText = await errorAlert.textContent();
  89  |       console.log('API Error displayed:', errorText);
  90  |       
  91  |       // Verify error is visible to user
  92  |       await expect(errorAlert).toBeVisible();
  93  |       
  94  |       await page.screenshot({ 
  95  |         path: 'test-results/screenshots/error-06-api-error-displayed.png',
  96  |         fullPage: true 
  97  |       });
  98  |     }
  99  |   });
  100 | 
  101 |   test('should clear previous errors when new scan is initiated', async ({ page }) => {
  102 |     await page.goto('/');
  103 | 
  104 |     // First, trigger a validation error
  105 |     await page.locator('button:has-text("Run Scan")').click();
  106 |     
  107 |     // Wait for error
  108 |     const errorAlert = page.locator('[role="alert"]');
  109 |     await expect(errorAlert.first()).toBeVisible({ timeout: 5000 });
  110 | 
  111 |     // Take screenshot of error
  112 |     await page.screenshot({ 
  113 |       path: 'test-results/screenshots/error-07-first-error.png',
  114 |       fullPage: true 
  115 |     });
  116 | 
  117 |     // Now enter tickers and scan again
  118 |     await page.locator('input[placeholder*="ticker"]').fill('AAPL');
  119 |     
  120 |     // Take screenshot before second scan
  121 |     await page.screenshot({ 
  122 |       path: 'test-results/screenshots/error-08-input-entered.png',
  123 |       fullPage: true 
  124 |     });
  125 | 
  126 |     await page.locator('button:has-text("Run Scan")').click();
  127 | 
  128 |     // The error should be cleared (either results show or new error appears)
  129 |     // Wait a moment for state to update
  130 |     await page.waitForTimeout(1000);
  131 | 
  132 |     await page.screenshot({ 
  133 |       path: 'test-results/screenshots/error-09-after-retry.png',
  134 |       fullPage: true 
  135 |     });
  136 | 
  137 |     console.log('✓ Error clearing behavior verified');
  138 |   });
  139 | });
  140 | 
```