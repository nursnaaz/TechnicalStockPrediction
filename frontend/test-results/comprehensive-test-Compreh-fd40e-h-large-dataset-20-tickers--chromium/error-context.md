# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: comprehensive-test.spec.ts >> Comprehensive E2E Test Suite with Extensive Screenshots >> Test with large dataset (20 tickers)
- Location: tests/e2e/comprehensive-test.spec.ts:240:3

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
        - textbox "Enter ticker symbols (e.g., AAPL, MSFT, GOOGL)" [disabled] [ref=e26]: AAPL, MSFT, NVDA, GOOGL, TSLA, AVGO, LLY, JNJ, UNH, HD, COST, PFE, ABBV, TMO, ORCL, ADBE, CRM, NKE, CSCO, PG
        - button "Run Scan" [disabled] [ref=e28]: Run Scan
      - paragraph [ref=e37]: Analyzing stocks...
```

# Test source

```ts
  175 |       // Step 15: Scroll through all results
  176 |       const lastRow = dataRows.last();
  177 |       await lastRow.scrollIntoViewIfNeeded();
  178 |       
  179 |       await page.screenshot({ 
  180 |         path: 'test-results/screenshots/comprehensive-14-last-result.png',
  181 |         fullPage: true 
  182 |       });
  183 | 
  184 |       // Step 16: Verify scores are present and visible
  185 |       console.log('✓ Verifying score column exists');
  186 |       
  187 |       // Just verify scores are visible - don't parse/compare since format may vary
  188 |       const firstRowCells = firstRow.locator('td');
  189 |       const cellCount = await firstRowCells.count();
  190 |       console.log(`✓ First row has ${cellCount} cells`);
  191 |       
  192 |       // Verify we have at least rank, ticker, score columns
  193 |       expect(cellCount).toBeGreaterThanOrEqual(3);
  194 |       console.log('✓ Results table has expected column structure');
  195 | 
  196 |       // Step 17: Test responsiveness - resize window
  197 |       await page.setViewportSize({ width: 1920, height: 1080 });
  198 |       await page.screenshot({ 
  199 |         path: 'test-results/screenshots/comprehensive-15-desktop-view.png',
  200 |         fullPage: true 
  201 |       });
  202 |       console.log('✓ Desktop view captured');
  203 | 
  204 |       await page.setViewportSize({ width: 768, height: 1024 });
  205 |       await page.screenshot({ 
  206 |         path: 'test-results/screenshots/comprehensive-16-tablet-view.png',
  207 |         fullPage: true 
  208 |       });
  209 |       console.log('✓ Tablet view captured');
  210 | 
  211 |       await page.setViewportSize({ width: 375, height: 667 });
  212 |       await page.screenshot({ 
  213 |         path: 'test-results/screenshots/comprehensive-17-mobile-view.png',
  214 |         fullPage: true 
  215 |       });
  216 |       console.log('✓ Mobile view captured');
  217 | 
  218 |       // Reset viewport
  219 |       await page.setViewportSize({ width: 1280, height: 720 });
  220 | 
  221 |       console.log('✅ ALL TESTS PASSED - Results displayed and verified');
  222 | 
  223 |     } else {
  224 |       // Handle error case
  225 |       const errorAlert = page.locator('[role="alert"]');
  226 |       await expect(errorAlert).toBeVisible();
  227 |       
  228 |       const errorText = await errorAlert.textContent();
  229 |       console.log(`⚠ Error displayed: ${errorText}`);
  230 |       
  231 |       await page.screenshot({ 
  232 |         path: 'test-results/screenshots/comprehensive-error-displayed.png',
  233 |         fullPage: true 
  234 |       });
  235 |       
  236 |       console.log('✓ Error handling verified - UI correctly displays error');
  237 |     }
  238 |   });
  239 | 
  240 |   test('Test with large dataset (20 tickers)', async ({ page }) => {
  241 |     await page.goto('/');
  242 |     
  243 |     await page.screenshot({ 
  244 |       path: 'test-results/screenshots/large-dataset-01-initial.png',
  245 |       fullPage: true 
  246 |     });
  247 | 
  248 |     // Enter 20 halal stocks
  249 |     const largeTickers = 'AAPL, MSFT, NVDA, GOOGL, TSLA, AVGO, LLY, JNJ, UNH, HD, COST, PFE, ABBV, TMO, ORCL, ADBE, CRM, NKE, CSCO, PG';
  250 |     
  251 |     const input = page.locator('input[placeholder*="ticker"]');
  252 |     await input.fill(largeTickers);
  253 |     
  254 |     await page.screenshot({ 
  255 |       path: 'test-results/screenshots/large-dataset-02-tickers-entered.png',
  256 |       fullPage: true 
  257 |     });
  258 |     console.log('✓ 20 tickers entered');
  259 | 
  260 |     await page.locator('button:has-text("Run Scan")').click();
  261 |     
  262 |     await page.screenshot({ 
  263 |       path: 'test-results/screenshots/large-dataset-03-scan-started.png',
  264 |       fullPage: true 
  265 |     });
  266 | 
  267 |     // Wait longer for large dataset
  268 |     await page.waitForTimeout(1000);
  269 |     await page.screenshot({ 
  270 |       path: 'test-results/screenshots/large-dataset-04-processing.png',
  271 |       fullPage: true 
  272 |     });
  273 | 
  274 |     const resultsOrError = page.locator('table, [role="alert"]');
> 275 |     await resultsOrError.waitFor({ timeout: 45000 }); // Longer timeout for 20 stocks
      |                          ^ Error: locator.waitFor: Test timeout of 30000ms exceeded.
  276 | 
  277 |     await page.screenshot({ 
  278 |       path: 'test-results/screenshots/large-dataset-05-completed.png',
  279 |       fullPage: true 
  280 |     });
  281 | 
  282 |     const resultsTable = page.locator('table');
  283 |     if (await resultsTable.isVisible()) {
  284 |       const dataRows = resultsTable.locator('tbody tr');
  285 |       const rowCount = await dataRows.count();
  286 |       
  287 |       console.log(`✓ Large dataset: ${rowCount} results displayed`);
  288 |       expect(rowCount).toBeLessThanOrEqual(20);
  289 | 
  290 |       // Capture top results
  291 |       await page.screenshot({ 
  292 |         path: 'test-results/screenshots/large-dataset-06-top-results.png',
  293 |         fullPage: true 
  294 |       });
  295 | 
  296 |       // Scroll to bottom results
  297 |       await dataRows.last().scrollIntoViewIfNeeded();
  298 |       await page.screenshot({ 
  299 |         path: 'test-results/screenshots/large-dataset-07-bottom-results.png',
  300 |         fullPage: true 
  301 |       });
  302 | 
  303 |       console.log('✅ Large dataset test passed');
  304 |     }
  305 |   });
  306 | 
  307 |   test('Test input variations and special characters', async ({ page }) => {
  308 |     await page.goto('/');
  309 | 
  310 |     const input = page.locator('input[placeholder*="ticker"]');
  311 | 
  312 |     // Test 1: Lowercase tickers
  313 |     await input.fill('aapl, msft, googl');
  314 |     await page.screenshot({ 
  315 |       path: 'test-results/screenshots/variations-01-lowercase.png',
  316 |       fullPage: true 
  317 |     });
  318 |     console.log('✓ Lowercase input captured');
  319 | 
  320 |     // Test 2: Mixed case
  321 |     await input.clear();
  322 |     await input.fill('AaPl, MsFt, GoOgL');
  323 |     await page.screenshot({ 
  324 |       path: 'test-results/screenshots/variations-02-mixed-case.png',
  325 |       fullPage: true 
  326 |     });
  327 |     console.log('✓ Mixed case input captured');
  328 | 
  329 |     // Test 3: Extra spaces
  330 |     await input.clear();
  331 |     await input.fill('  AAPL  ,   MSFT   ,  GOOGL  ');
  332 |     await page.screenshot({ 
  333 |       path: 'test-results/screenshots/variations-03-extra-spaces.png',
  334 |       fullPage: true 
  335 |     });
  336 |     console.log('✓ Extra spaces input captured');
  337 | 
  338 |     // Test 4: Tabs and newlines (if supported)
  339 |     await input.clear();
  340 |     await input.fill('AAPL\tMSFT\nGOOGL');
  341 |     await page.screenshot({ 
  342 |       path: 'test-results/screenshots/variations-04-special-separators.png',
  343 |       fullPage: true 
  344 |     });
  345 |     console.log('✓ Special separators input captured');
  346 | 
  347 |     // Test 5: Single ticker
  348 |     await input.clear();
  349 |     await input.fill('AAPL');
  350 |     await page.screenshot({ 
  351 |       path: 'test-results/screenshots/variations-05-single-ticker.png',
  352 |       fullPage: true 
  353 |     });
  354 |     console.log('✓ Single ticker input captured');
  355 | 
  356 |     console.log('✅ Input variation tests completed');
  357 |   });
  358 | 
  359 |   test('UI interaction and state persistence', async ({ page }) => {
  360 |     await page.goto('/');
  361 | 
  362 |     const input = page.locator('input[placeholder*="ticker"]');
  363 |     
  364 |     // Enter tickers
  365 |     await input.fill('AAPL, MSFT');
  366 |     await page.screenshot({ 
  367 |       path: 'test-results/screenshots/interaction-01-input-filled.png',
  368 |       fullPage: true 
  369 |     });
  370 | 
  371 |     // Focus and blur
  372 |     await input.focus();
  373 |     await page.screenshot({ 
  374 |       path: 'test-results/screenshots/interaction-02-input-focused.png',
  375 |       fullPage: true 
```