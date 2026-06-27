# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: results-display.spec.ts >> Results Display >> should display market regime badge correctly
- Location: tests/e2e/results-display.spec.ts:4:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: .awsui-badge, [class*="badge"], text=/bullish|bearish|neutral/i >> nth=0
Expected: visible
Error: Unexpected token "=" while parsing css selector ".awsui-badge, [class*="badge"], text=/bullish|bearish|neutral/i". Did you mean to CSS.escape it?

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for .awsui-badge, [class*="badge"], text=/bullish|bearish|neutral/i >> nth=0

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
        - textbox "Enter ticker symbols (e.g., AAPL, MSFT, GOOGL)" [ref=e26]: AAPL, MSFT
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
            - heading "Ranked Results (2)" [level=2] [ref=e55]:
              - text: Ranked Results
              - generic [ref=e56]: (2)
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
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('Results Display', () => {
  4   |   test('should display market regime badge correctly', async ({ page }) => {
  5   |     // Navigate to the application
  6   |     await page.goto('/');
  7   | 
  8   |     // Take screenshot of initial state
  9   |     await page.screenshot({ 
  10  |       path: 'test-results/screenshots/results-01-initial.png',
  11  |       fullPage: true 
  12  |     });
  13  | 
  14  |     // Enter tickers and run scan
  15  |     await page.locator('input[placeholder*="ticker"]').fill('AAPL, MSFT');
  16  |     await page.locator('button:has-text("Run Scan")').click();
  17  | 
  18  |     // Wait for results or error
  19  |     const resultsOrError = page.locator('table, [role="alert"]');
  20  |     await resultsOrError.waitFor({ timeout: 30000 });
  21  | 
  22  |     // Take screenshot of results
  23  |     await page.screenshot({ 
  24  |       path: 'test-results/screenshots/results-02-after-scan.png',
  25  |       fullPage: true 
  26  |     });
  27  | 
  28  |     // Check if results are displayed (backend must be running)
  29  |     const resultsTable = page.locator('table');
  30  |     if (await resultsTable.isVisible()) {
  31  |       // Look for market regime badge
  32  |       const regimeBadge = page.locator('.awsui-badge, [class*="badge"], text=/bullish|bearish|neutral/i');
> 33  |       await expect(regimeBadge.first()).toBeVisible();
      |                                         ^ Error: expect(locator).toBeVisible() failed
  34  | 
  35  |       // Verify badge contains one of the valid regime values
  36  |       const badgeText = await regimeBadge.first().textContent();
  37  |       expect(badgeText?.toLowerCase()).toMatch(/bullish|bearish|neutral/);
  38  | 
  39  |       // Take screenshot highlighting regime badge
  40  |       await page.screenshot({ 
  41  |         path: 'test-results/screenshots/results-03-regime-badge.png',
  42  |         fullPage: true 
  43  |       });
  44  | 
  45  |       console.log('✓ Market regime badge displayed:', badgeText);
  46  |     } else {
  47  |       console.log('⚠ Backend not running, skipping regime badge verification');
  48  |     }
  49  |   });
  50  | 
  51  |   test('should display results table with all required columns', async ({ page }) => {
  52  |     await page.goto('/');
  53  | 
  54  |     // Enter tickers and run scan
  55  |     await page.locator('input[placeholder*="ticker"]').fill('AAPL, MSFT, GOOGL');
  56  |     await page.locator('button:has-text("Run Scan")').click();
  57  | 
  58  |     // Wait for results or error
  59  |     const resultsOrError = page.locator('table, [role="alert"]');
  60  |     await resultsOrError.waitFor({ timeout: 30000 });
  61  | 
  62  |     const resultsTable = page.locator('table');
  63  |     if (await resultsTable.isVisible()) {
  64  |       // Verify table is visible
  65  |       await expect(resultsTable).toBeVisible();
  66  | 
  67  |       // Verify table headers
  68  |       const headers = resultsTable.locator('thead th, thead [role="columnheader"]');
  69  |       const headerCount = await headers.count();
  70  |       expect(headerCount).toBeGreaterThan(0);
  71  | 
  72  |       // Take screenshot of table structure
  73  |       await page.screenshot({ 
  74  |         path: 'test-results/screenshots/results-04-table-structure.png',
  75  |         fullPage: true 
  76  |       });
  77  | 
  78  |       // Verify expected columns exist (case-insensitive)
  79  |       const headerTexts = await headers.allTextContents();
  80  |       const headerString = headerTexts.join(' ').toLowerCase();
  81  |       
  82  |       expect(headerString).toContain('rank');
  83  |       expect(headerString).toContain('ticker');
  84  |       expect(headerString).toContain('score');
  85  | 
  86  |       console.log('✓ Table columns verified:', headerTexts);
  87  | 
  88  |       // Verify data rows exist
  89  |       const dataRows = resultsTable.locator('tbody tr');
  90  |       const rowCount = await dataRows.count();
  91  |       expect(rowCount).toBeGreaterThan(0);
  92  | 
  93  |       console.log('✓ Table has', rowCount, 'data rows');
  94  | 
  95  |       // Take screenshot of populated table
  96  |       await page.screenshot({ 
  97  |         path: 'test-results/screenshots/results-05-table-data.png',
  98  |         fullPage: true 
  99  |       });
  100 |     } else {
  101 |       console.log('⚠ Backend not running, skipping table verification');
  102 |     }
  103 |   });
  104 | 
  105 |   test('should display ticker scores with proper formatting', async ({ page }) => {
  106 |     await page.goto('/');
  107 | 
  108 |     // Enter tickers
  109 |     await page.locator('input[placeholder*="ticker"]').fill('AAPL, MSFT');
  110 |     await page.locator('button:has-text("Run Scan")').click();
  111 | 
  112 |     // Wait for results
  113 |     const resultsOrError = page.locator('table, [role="alert"]');
  114 |     await resultsOrError.waitFor({ timeout: 30000 });
  115 | 
  116 |     const resultsTable = page.locator('table');
  117 |     if (await resultsTable.isVisible()) {
  118 |       // Look for score badges or score cells
  119 |       const scoreCells = resultsTable.locator('tbody td .awsui-badge, tbody td[class*="score"]');
  120 |       
  121 |       if (await scoreCells.count() > 0) {
  122 |         // Verify at least one score is displayed
  123 |         await expect(scoreCells.first()).toBeVisible();
  124 | 
  125 |         // Take screenshot of score formatting
  126 |         await page.screenshot({ 
  127 |           path: 'test-results/screenshots/results-06-score-formatting.png',
  128 |           fullPage: true 
  129 |         });
  130 | 
  131 |         console.log('✓ Score badges/cells displayed');
  132 |       }
  133 | 
```