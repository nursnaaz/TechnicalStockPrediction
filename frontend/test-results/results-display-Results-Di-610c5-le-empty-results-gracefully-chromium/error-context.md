# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: results-display.spec.ts >> Results Display >> should handle empty results gracefully
- Location: tests/e2e/results-display.spec.ts:215:3

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
        - textbox "Enter ticker symbols (e.g., AAPL, MSFT, GOOGL)" [ref=e26]: INVALIDTICKER999
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
  130 | 
  131 |         console.log('✓ Score badges/cells displayed');
  132 |       }
  133 | 
  134 |       // Verify ticker symbols are displayed
  135 |       const tickerCells = resultsTable.locator('tbody td:has-text("AAPL"), tbody td:has-text("MSFT")');
  136 |       if (await tickerCells.count() > 0) {
  137 |         await expect(tickerCells.first()).toBeVisible();
  138 |         console.log('✓ Ticker symbols displayed in results');
  139 |       }
  140 |     }
  141 |   });
  142 | 
  143 |   test('should display ranked results in descending order', async ({ page }) => {
  144 |     await page.goto('/');
  145 | 
  146 |     // Enter multiple tickers for ranking
  147 |     await page.locator('input[placeholder*="ticker"]').fill('AAPL, MSFT, GOOGL, TSLA');
  148 |     await page.locator('button:has-text("Run Scan")').click();
  149 | 
  150 |     // Wait for results
  151 |     const resultsOrError = page.locator('table, [role="alert"]');
  152 |     await resultsOrError.waitFor({ timeout: 30000 });
  153 | 
  154 |     const resultsTable = page.locator('table');
  155 |     if (await resultsTable.isVisible()) {
  156 |       // Get all data rows
  157 |       const dataRows = resultsTable.locator('tbody tr');
  158 |       const rowCount = await dataRows.count();
  159 | 
  160 |       if (rowCount > 1) {
  161 |         // Verify rank column exists and shows 1, 2, 3...
  162 |         const rankCells = resultsTable.locator('tbody tr td:first-child');
  163 |         const firstRank = await rankCells.first().textContent();
  164 |         
  165 |         // First rank should be 1
  166 |         expect(firstRank?.trim()).toBe('1');
  167 | 
  168 |         console.log('✓ Results are ranked, first rank is 1');
  169 | 
  170 |         // Take screenshot of ranked results
  171 |         await page.screenshot({ 
  172 |           path: 'test-results/screenshots/results-07-ranked-order.png',
  173 |           fullPage: true 
  174 |         });
  175 |       }
  176 |     }
  177 |   });
  178 | 
  179 |   test('should display signal indicators for each ticker', async ({ page }) => {
  180 |     await page.goto('/');
  181 | 
  182 |     // Enter tickers
  183 |     await page.locator('input[placeholder*="ticker"]').fill('AAPL');
  184 |     await page.locator('button:has-text("Run Scan")').click();
  185 | 
  186 |     // Wait for results
  187 |     const resultsOrError = page.locator('table, [role="alert"]');
  188 |     await resultsOrError.waitFor({ timeout: 30000 });
  189 | 
  190 |     const resultsTable = page.locator('table');
  191 |     if (await resultsTable.isVisible()) {
  192 |       // Look for signal indicators (badges, icons, or text)
  193 |       const signalIndicators = resultsTable.locator('tbody .awsui-badge, tbody [class*="signal"], tbody [class*="badge"]');
  194 |       
  195 |       // Take screenshot of signals column
  196 |       await page.screenshot({ 
  197 |         path: 'test-results/screenshots/results-08-signal-indicators.png',
  198 |         fullPage: true 
  199 |       });
  200 | 
  201 |       if (await signalIndicators.count() > 0) {
  202 |         console.log('✓ Signal indicators found:', await signalIndicators.count());
  203 |       }
  204 | 
  205 |       // Verify the signals column exists
  206 |       const headers = await resultsTable.locator('thead th, thead [role="columnheader"]').allTextContents();
  207 |       const hasSignalsColumn = headers.some(h => h.toLowerCase().includes('signal'));
  208 |       
  209 |       if (hasSignalsColumn) {
  210 |         console.log('✓ Signals column present in table');
  211 |       }
  212 |     }
  213 |   });
  214 | 
  215 |   test('should handle empty results gracefully', async ({ page }) => {
  216 |     await page.goto('/');
  217 | 
  218 |     // Enter potentially invalid tickers that might return empty results
  219 |     await page.locator('input[placeholder*="ticker"]').fill('INVALIDTICKER999');
  220 |     
  221 |     await page.screenshot({ 
  222 |       path: 'test-results/screenshots/results-09-before-invalid-scan.png',
  223 |       fullPage: true 
  224 |     });
  225 | 
  226 |     await page.locator('button:has-text("Run Scan")').click();
  227 | 
  228 |     // Wait for response
  229 |     const resultsOrError = page.locator('table, [role="alert"]');
> 230 |     await resultsOrError.waitFor({ timeout: 30000 });
      |                          ^ Error: locator.waitFor: Test timeout of 30000ms exceeded.
  231 | 
  232 |     // Take screenshot of result
  233 |     await page.screenshot({ 
  234 |       path: 'test-results/screenshots/results-10-invalid-ticker-result.png',
  235 |       fullPage: true 
  236 |     });
  237 | 
  238 |     // Verify UI shows either empty table or error message
  239 |     const errorMessage = page.locator('[role="alert"]');
  240 |     const emptyTable = page.locator('table tbody:has-text("No")');
  241 |     
  242 |     const hasErrorOrEmpty = await errorMessage.isVisible() || await emptyTable.isVisible();
  243 |     
  244 |     // Either error or empty state is acceptable
  245 |     console.log('✓ Invalid ticker handling verified');
  246 |   });
  247 | });
  248 | 
```