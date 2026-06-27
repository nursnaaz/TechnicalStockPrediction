# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: happy-path.spec.ts >> Happy Path - Complete Scan Workflow >> should successfully complete scan workflow from input to results
- Location: tests/e2e/happy-path.spec.ts:4:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: [data-testid*="regime"], .awsui-badge, text=/bullish|bearish|neutral/i >> nth=0
Expected: visible
Error: Unexpected token "=" while parsing css selector "[data-testid*="regime"], .awsui-badge, text=/bullish|bearish|neutral/i". Did you mean to CSS.escape it?

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for [data-testid*="regime"], .awsui-badge, text=/bullish|bearish|neutral/i >> nth=0

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
        - textbox "Enter ticker symbols (e.g., AAPL, MSFT, GOOGL)" [ref=e26]: AAPL, MSFT, GOOGL
        - button "Run Scan" [ref=e28] [cursor=pointer]
      - generic [ref=e30]:
        - generic [ref=e33]:
          - heading "Market Regime" [level=2] [ref=e38]
          - generic [ref=e42]:
            - generic [ref=e44]:
              - img
            - generic [ref=e45]: Neutral Market
        - generic [ref=e48]:
          - generic [ref=e52]:
            - heading "Ranked Results (3)" [level=2] [ref=e55]:
              - text: Ranked Results
              - generic [ref=e56]: (3)
            - paragraph [ref=e57]: Stocks ranked by bullish score
          - table "Ranked Results" [ref=e61]:
            - rowgroup [ref=e62]:
              - row "Rank Ticker Bullish Score Price Active Signals" [ref=e63]:
                - columnheader "Rank" [ref=e64]:
                  - generic [ref=e66]: Rank
                - columnheader "Ticker" [ref=e67]:
                  - generic [ref=e69]: Ticker
                - columnheader "Bullish Score" [ref=e70]:
                  - generic [ref=e72]: Bullish Score
                - columnheader "Price" [ref=e73]:
                  - generic [ref=e75]: Price
                - columnheader "Active Signals" [ref=e76]:
                  - generic [ref=e78]: Active Signals
            - rowgroup [ref=e79]:
              - row "1 AAPL 15 $283.78 SMA50 EMA20 MACD MACD+ Vol RS" [ref=e80]:
                - cell "1" [ref=e81]:
                  - generic [ref=e83]: "1"
                - cell "AAPL" [ref=e84]:
                  - strong [ref=e86]: AAPL
                - cell "15" [ref=e87]:
                  - generic [ref=e89]: "15"
                - cell "$283.78" [ref=e90]:
                  - generic [ref=e91]: $283.78
                - cell "SMA50 EMA20 MACD MACD+ Vol RS" [ref=e92]:
                  - generic [ref=e94]:
                    - generic [ref=e96]: SMA50
                    - generic [ref=e98]: EMA20
                    - generic [ref=e100]: MACD
                    - generic [ref=e102]: MACD+
                    - generic [ref=e104]: Vol
                    - generic [ref=e106]: RS
              - row "2 MSFT 15 $372.97 SMA50 EMA20 MACD MACD+ Vol RS" [ref=e107]:
                - cell "2" [ref=e108]:
                  - generic [ref=e110]: "2"
                - cell "MSFT" [ref=e111]:
                  - strong [ref=e113]: MSFT
                - cell "15" [ref=e114]:
                  - generic [ref=e116]: "15"
                - cell "$372.97" [ref=e117]:
                  - generic [ref=e118]: $372.97
                - cell "SMA50 EMA20 MACD MACD+ Vol RS" [ref=e119]:
                  - generic [ref=e121]:
                    - generic [ref=e123]: SMA50
                    - generic [ref=e125]: EMA20
                    - generic [ref=e127]: MACD
                    - generic [ref=e129]: MACD+
                    - generic [ref=e131]: Vol
                    - generic [ref=e133]: RS
              - row "3 GOOGL 15 $337.39 SMA50 EMA20 MACD MACD+ Vol RS" [ref=e134]:
                - cell "3" [ref=e135]:
                  - generic [ref=e137]: "3"
                - cell "GOOGL" [ref=e138]:
                  - strong [ref=e140]: GOOGL
                - cell "15" [ref=e141]:
                  - generic [ref=e143]: "15"
                - cell "$337.39" [ref=e144]:
                  - generic [ref=e145]: $337.39
                - cell "SMA50 EMA20 MACD MACD+ Vol RS" [ref=e146]:
                  - generic [ref=e148]:
                    - generic [ref=e150]: SMA50
                    - generic [ref=e152]: EMA20
                    - generic [ref=e154]: MACD
                    - generic [ref=e156]: MACD+
                    - generic [ref=e158]: Vol
                    - generic [ref=e160]: RS
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('Happy Path - Complete Scan Workflow', () => {
  4   |   test('should successfully complete scan workflow from input to results', async ({ page }) => {
  5   |     // Navigate to the application
  6   |     await page.goto('/');
  7   | 
  8   |     // Take screenshot of initial state
  9   |     await page.screenshot({ 
  10  |       path: 'test-results/screenshots/happy-path-01-initial-state.png',
  11  |       fullPage: true 
  12  |     });
  13  | 
  14  |     // Verify page loaded correctly
  15  |     await expect(page.locator('h1')).toContainText('Bullish Stock Scanner');
  16  | 
  17  |     // Enter ticker symbols in the input field
  18  |     const input = page.locator('input[placeholder*="ticker"]');
  19  |     await expect(input).toBeVisible();
  20  |     await input.fill('AAPL, MSFT, GOOGL');
  21  | 
  22  |     // Take screenshot after input
  23  |     await page.screenshot({ 
  24  |       path: 'test-results/screenshots/happy-path-02-after-input.png',
  25  |       fullPage: true 
  26  |     });
  27  | 
  28  |     // Click the "Run Scan" button
  29  |     const scanButton = page.locator('button:has-text("Run Scan")');
  30  |     await expect(scanButton).toBeVisible();
  31  |     
  32  |     // Note: The backend must be running for this test to pass
  33  |     // We'll click and wait for either results or error
  34  |     await scanButton.click();
  35  | 
  36  |     // Take screenshot of loading state
  37  |     await page.waitForTimeout(500); // Give time for loading state to appear
  38  |     await page.screenshot({ 
  39  |       path: 'test-results/screenshots/happy-path-03-loading-state.png',
  40  |       fullPage: true 
  41  |     });
  42  | 
  43  |     // Wait for results to appear (or error)
  44  |     // Check for either results table or error message
  45  |     const resultsOrError = page.locator('table, [role="alert"]');
  46  |     await resultsOrError.waitFor({ timeout: 30000 });
  47  | 
  48  |     // Take screenshot of final state
  49  |     await page.screenshot({ 
  50  |       path: 'test-results/screenshots/happy-path-04-final-state.png',
  51  |       fullPage: true 
  52  |     });
  53  | 
  54  |     // If we got results, verify the structure
  55  |     const resultsTable = page.locator('table');
  56  |     if (await resultsTable.isVisible()) {
  57  |       // Verify market regime badge is displayed
  58  |       const regimeBadge = page.locator('[data-testid*="regime"], .awsui-badge, text=/bullish|bearish|neutral/i');
> 59  |       await expect(regimeBadge.first()).toBeVisible();
      |                                         ^ Error: expect(locator).toBeVisible() failed
  60  | 
  61  |       // Verify results table has expected columns
  62  |       await expect(resultsTable).toBeVisible();
  63  |       
  64  |       // Verify table headers
  65  |       const headers = resultsTable.locator('th');
  66  |       await expect(headers).toContainText(['Rank', 'Ticker', 'Score', 'Price']);
  67  | 
  68  |       // Verify at least one row of data
  69  |       const dataRows = resultsTable.locator('tbody tr');
  70  |       await expect(dataRows.first()).toBeVisible();
  71  | 
  72  |       // Take screenshot of results with annotations
  73  |       await page.screenshot({ 
  74  |         path: 'test-results/screenshots/happy-path-05-results-verified.png',
  75  |         fullPage: true 
  76  |       });
  77  | 
  78  |       console.log('✓ Happy path completed successfully - results displayed');
  79  |     } else {
  80  |       // If we got an error instead, log it for debugging
  81  |       const errorMessage = page.locator('[role="alert"]');
  82  |       const errorText = await errorMessage.textContent();
  83  |       console.log('⚠ Backend may not be running. Error:', errorText);
  84  |       
  85  |       // This is still a valid test result - the UI handled the error correctly
  86  |       await expect(errorMessage).toBeVisible();
  87  |     }
  88  |   });
  89  | 
  90  |   test('should display all expected UI elements in results', async ({ page }) => {
  91  |     await page.goto('/');
  92  | 
  93  |     // Enter tickers and run scan
  94  |     await page.locator('input[placeholder*="ticker"]').fill('AAPL, MSFT');
  95  |     await page.locator('button:has-text("Run Scan")').click();
  96  | 
  97  |     // Wait for response
  98  |     const resultsOrError = page.locator('table, [role="alert"]');
  99  |     await resultsOrError.waitFor({ timeout: 30000 });
  100 | 
  101 |     // Only verify UI elements if results are displayed
  102 |     const resultsTable = page.locator('table');
  103 |     if (await resultsTable.isVisible()) {
  104 |       // Verify market regime is displayed
  105 |       await expect(page.locator('text=/market.*regime/i, text=/bullish|bearish|neutral/i').first()).toBeVisible();
  106 | 
  107 |       // Verify results table structure
  108 |       await expect(resultsTable.locator('thead')).toBeVisible();
  109 |       await expect(resultsTable.locator('tbody')).toBeVisible();
  110 | 
  111 |       // Verify score badges are present
  112 |       const scoreBadges = resultsTable.locator('.awsui-badge, [class*="badge"]');
  113 |       if (await scoreBadges.count() > 0) {
  114 |         await expect(scoreBadges.first()).toBeVisible();
  115 |       }
  116 | 
  117 |       // Take final screenshot
  118 |       await page.screenshot({ 
  119 |         path: 'test-results/screenshots/happy-path-ui-elements.png',
  120 |         fullPage: true 
  121 |       });
  122 |     }
  123 |   });
  124 | });
  125 | 
```