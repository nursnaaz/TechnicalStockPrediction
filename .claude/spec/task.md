# V3 Implementation Plan — High-Precision Bullish Scanner

> **Source:** Implements `design.md`, which implements `requirement.md` (R1–R10). Mirrors the house
> format in `.kiro/specs/bullish-stock-scanner/tasks.md`: TDD checkbox tasks grouped by phase, each with
> implementation steps, mandatory unit tests, property-test references, and `_Requirements: Rn_`
> traceability. A wave-based dependency graph is at the end.

## Overview

This plan implements the V3 upgrade as **7 changes across 4 phases**, bottom-up:
**indicators/models → gates → scoring → orchestrator → validation**.

**TDD is mandatory — no task is complete without unit tests.** A task is **not complete** until:
(1) code implemented, (2) **detailed unit tests written for that task**, (3) tests pass with >80%
coverage, (4) referenced property tests pass. **Without unit testing, treat the task as incomplete.**

Testing happens at **four levels**, all required:
1. **Unit tests** — per task, mandatory (Phases 1–4).
2. **Integration tests** — at component checkpoints (Phase 4.x, `tests/integration/`).
3. **Backtest validation suite** — V1–V4 (Phase 4).
4. **Extensive Playwright feature/E2E tests** — Phase 5, the **FINAL completion gate**. All tasks are
   considered complete **only** after the full Playwright suite passes against a live stack.

**Anti-overfitting constraints (enforced throughout):** ≤7 changes total; no date-specific tuning; 3–5
parameters per component; no machine learning; if out-of-sample precision <75% → simplify.

---

## Tasks

### Phase 1 — Market Regime Gate

- [ ] 1.1 Add SPY regime indicators (EMA21 + SMA200 series + 5-day persistence inputs)
  - 🛑 **Fetch-window fix (R9, blocking):** the SPY fetch in `core/regime_analyzer.py` (and the SPY
    `market_data` fetch in `core/orchestrator.py:121`) must request **≈365 calendar days** (not 250) so
    SPY SMA200 is computable; assert ≥252 trading bars returned. Without this the regime gate silently
    defaults to NEUTRAL and P1/V2 break.
  - **Implement:** in the regime path (`core/indicator_calculator.py` helpers or `regime_analyzer`),
    compute SMA200 series and EMA21 from SPY closes; expose the last 5 closes vs SMA200.
  - **Unit tests:** SMA200 correctness on known series; EMA21 correctness; last-5-above / last-5-below
    detection on synthetic SPY data; assert insufficient history fails loudly.
  - **Definition of done:** tests pass, >80% coverage.
  - _Requirements: R1, R8, R9, R10_

- [ ] 1.2 Rewrite `MarketRegimeAnalyzer` to return `RegimeResult`
  - **Implement:** new `RegimeResult(regime, threshold, emit_signals)`; classification per design §3.1
    (BULLISH→thr 65/emit; BEARISH→emit False; NEUTRAL→thr 75/emit); keep `as_of_date`; API-failure →
    NEUTRAL.
  - **Unit tests (rewrite `tests/unit/test_regime_analyzer.py`):** assert the full
    `(regime, threshold, emit_signals)` tuple per case — BULLISH→(_,65,True), NEUTRAL→(_,75,True),
    BEARISH→(_,_,False), API-failure→(NEUTRAL,75,True); 5-day persistence both sides (4-of-5 above →
    NEUTRAL not BULLISH; 4-of-5 below → NEUTRAL not BEARISH; 5-of-5 → BULLISH/BEARISH); price exactly at
    SMA200 (equality → NEUTRAL).
  - _Requirements: R1_

- [ ] 1.3 Orchestrator: regime gate short-circuit + thread threshold
  - **Implement:** call `analyze_regime` first; if `emit_signals` is False, return `ScanResponse` with
    empty `ranked_tickers`; otherwise **thread** `regime.threshold` so it is available to the BUY
    decision. (This task only carries the value; the actual `score >= threshold` filter is implemented
    once in 3.1's PASS 2 and finalized in 4.1 — avoid duplicating the comparison.)
  - **Also replace** the legacy `ScanError("All tickers failed…")` guard so an empty candidate list is a
    VALID result (raise only when every fetch ERRORED, not when tickers were validly filtered out).
  - **Unit tests (`tests/unit/test_orchestrator.py`):** BEARISH → zero candidates, no scoring calls
    (assert scoring engine not invoked); BULLISH/NEUTRAL → scoring proceeds with correct threshold;
    all-filtered-out → empty `ranked_tickers` (no error); all-fetch-errored → ScanError.
  - _Requirements: R1, R7_

- [ ] 1.4 Property test — bearish gate
  - **Property P1: Bearish Regime Emits Zero Candidates.** **Validates: R1**
  - **Validation hook:** wire up V2 (March 2026, Top 50 → expect 0 BUYs).
  - _Requirements: R1_

### Phase 2 — Eliminate False Positives

- [ ] 2.1 Add SMA150, SMA200, SMA200 slope, 52-week high/low (+ fetch-window fix)
  - 🛑 **Fetch-window fix (R9, blocking):** raise the **per-ticker** fetch in `core/orchestrator.py:134`
    (and the shared default in `core/api_client.py`) to **≈365 calendar days**; `days=250` yields only
    ~178 trading bars → SMA200/slope/52-wk all `None` → every hard filter fails → zero candidates in
    all regimes. **Assert `len(prices) >= 252`** before gate computation so shortfalls fail loudly.
  - **Implement (`core/indicator_calculator.py`, `core/models.py`):** add `sma_150`, `sma_200`,
    `sma_200_slope` (`_sma_slope(prices, 200, lookback=20)`), `week52_high`, `week52_low` (from
    `prices[-252:]`); add the matching optional fields to `TechnicalIndicators`.
  - **Unit tests (`tests/unit/test_indicator_calculator.py`):** SMA150/200 correctness; slope sign
    (rising/falling/flat); 52-wk hi/lo; **per-threshold history boundaries** — 199 vs 200 bars
    (`sma_200` None vs value), 219 vs 220 (`sma_200_slope`), 251 vs 252 (`week52_*`); mock-assert the
    fetch was called with ≈365 `days` at each call site; post-fetch `len(prices) >= 252` assertion.
  - **Property P9: SMA(200) Slope Sign Correctness.** **Validates: R10**
  - **Property P10: New Indicator Correctness & History Sufficiency.** **Validates: R8, R9**
  - _Requirements: R8, R9, R10_

- [ ] 2.2 Add `passes_hard_filters()` and gate in orchestrator
  - **Implement (`core/scoring_engine.py`):** `passes_hard_filters(price, indicators) -> (bool, dict)`
    for H1–H6 (None indicator → that check fails). **(`core/orchestrator.py`):** call before
    `calculate_enhanced_score`; on failure exclude ticker (score 0).
  - **Unit tests:** each H1–H6 pass and fail in isolation; all-pass; **per-check None→fail** (set only
    that check's indicator(s) to None — incl. H4's two: `sma_50`/`sma_200` — and assert only that check
    is False); **boundary equality** — strict checks fail on equality (`price==sma_200`→H1 fail,
    `slope==0`→H2 fail, `sma_50==sma_200`→H4 fail), inclusive checks pass on equality
    (`price==1.30*low`→H5 pass, `price==0.75*high`→H6 pass); orchestrator excludes failed tickers.
  - **Property P2: Hard-Filter Failure Forces Score Zero.** **Validates: R2**
  - _Requirements: R2, R8, R9, R10_

- [ ] 2.3 Remove recovery bonus
  - **Implement:** delete the `RECOVERY BONUS (0–25 pts)` block from `calculate_score()`.
  - **Unit tests (rewrite affected `tests/unit/test_scoring_engine.py`):** a below-MA stock no longer
    gets recovery points and (combined with 2.2) is gated out; **regression** — a fixture that earned a
    recovery bonus in V2 now scores lower by the removed 0–25 band (proves the block is gone, not merely
    low for other reasons).
  - **Property P3: No Credit Below Moving Averages.** **Validates: R3**
  - _Requirements: R3_

- [ ] 2.4 Strengthen extension penalty + momentum divergence
  - **Implement:** rewrite extension section — cap −15 → −25; tiers per requirement.md R4
    (dist-above-SMA50 0–10, RSI overbought 0–8, momentum divergence 0–7; `-= min(penalty, 25)`).
  - **Unit tests:** enumerate ALL tiers with boundary values — dist exactly 7/10/15% (strict: 15→10,
    10→7, 7→4), RSI exactly 65/70/75 (strict: 75→8, 70→5, 65→2; RSI==65 → 0), ROC exactly 0/−1/−3
    (gated on dist>5%: <−3→7, <−1→5, <0→3); `dist<=5%` ⇒ divergence block contributes 0 regardless of
    ROC; cap never exceeds −25; penalty never positive.
  - **Note (score floor):** the final `max(score, 0)` floor (P8) is added in task 4.1; intermediate
    scores in this task's tests may be negative before that clamp — assert on the penalty value, not the
    final floored score, until 4.1 lands.
  - **Property P4: Extension Penalty Bounded at −25.** **Validates: R4**
  - _Requirements: R4_

- [ ] 2.5 Checkpoint — gates + penalties working
  - Verify Phase 1–2 unit + property tests pass, >80% coverage. Confirm KO/PG/JNJ (Mar 2026) are gated
    or penalized below threshold. Ask the user if questions arise before Phase 3.

### Phase 3 — Improve Signal Quality

- [ ] 3.1 RS percentile (two-pass orchestrator + scoring param)
  - **Implement (`core/orchestrator.py`):** Pass 1 computes indicators + raw RS for all tickers; derive
    percentile across universe; Pass 2 passes `rs_percentile` into scoring.
    **(`core/scoring_engine.py`):** `calculate_score(..., rs_percentile=None)` strength tiers
    (≥90→10, ≥70→7, ≥50→4, else 0); thread through `calculate_enhanced_score`.
  - **Unit tests:** percentile computation across a universe (incl. tie/duplicate RS → min-rank);
    exact tier boundaries (percentile 90→10, 70→7, 50→4, 49.9→0); empty-universe / single-ticker →
    `pct()` returns 0.0; `None` RS → 0.0 (no crash).
  - **Property P5: RS-Percentile Scoring Is Monotonic.** **Validates: R5**
  - _Requirements: R5_

- [ ] 3.2 Indicator divergence penalty
  - **Implement:** after component scoring, evaluate {RSI>50, MACD>signal, ROC>0, price>SMA50} counting
    only non-`None` indicators; `agreement = max(bull,bear)/n`; `< 0.6 → −8`, `<= 0.75 → −4`; skip when
    fewer than 2 signals available. (⚠️ middle tier is `<= 0.75` — a strict `< 0.75` makes the −4 tier
    dead code since 3-1 splits give exactly 0.75; `None`-aware denominator preserves P8.)
  - **Unit tests:** 4-0/3-1/2-2 splits map to 0 / −4 / −8; exactly 0.75 → −4 (not 0); `None` signals
    reduce the denominator; <2 signals → no penalty.
  - **Property P6: Divergence Penalty Thresholds.** **Validates: R6**
  - _Requirements: R6_

### Phase 4 — Rebalance + Validation

- [ ] 4.1 Score budget rebalance + regime thresholds
  - **Implement:** confirm 5×0–20 components (post-recovery-removal) + penalties (≤−25, ≤−8); clamp
    [0,100]; BUY iff `score >= regime.threshold` and regime ≠ BEARISH (in orchestrator).
  - **Unit tests:** max-score path = 100; heavy-penalty path floors at 0; **all-None indicators →
    `isinstance(score, int)` in [0,100] without raising** (P8 core case); BUY at exactly 65 (BULLISH) and
    75 (NEUTRAL) → BUY, and just-below (64 BULLISH, 74 NEUTRAL) → no BUY.
  - **Property P7: Regime-Aware BUY Decision.** **Validates: R7, R1**
  - **Property P8: Score Bounds.** **Validates: R7, R8**
  - _Requirements: R7_

- [ ] 4.2 Align backtest predicted-bullish with regime-aware BUY
  - **Implement (`backtest/engine.py`):** replace `score >= 70` predicted-bullish with the regime-aware
    decision (threshold by regime; BEARISH ⇒ no prediction). Keep targets +10%/+20%, stop −7%, actual
    `max_gain >= 5%`.
  - **Also update** stale `description=` strings in `backtest_models.py` (`TradeResult.predicted_bullish`
    "True if score >= 70", `confusion_matrix` "score>=70 vs max_gain>=5%") to the regime-aware
    definition, so API docs aren't misleading.
  - **Unit tests (`tests/backtest/`):** predicted-bullish matches shipped BUY logic; **a BEARISH
    backtest date yields 0 predicted-bullish** (direct assertion, not only via 4.4); confusion matrix
    consistent.
  - _Requirements: R7_

- [ ] 4.3 Integration tests (backend) — `tests/integration/test_v3_pipeline.py`
  - **Test infra (prereq):** no `conftest.py` exists today; existing integration tests return ONE
    `sample_stock_data` for all `fetch_stock_data` calls. V3 needs a **per-ticker `side_effect` fixture**:
    build a `dict[ticker -> StockData]` (each ≥**260 bars**, `"SPY"` → market series) and
    `AsyncMock(side_effect=async fetch(ticker, days, as_of_date=None): data[ticker])`. **Bump every
    synthetic fixture to ≥252 bars** (the existing 250-bar `sample_stock_data` will otherwise make
    `week52_*`=None → H5/H6 fail).
  - **IT-1** regime gate → orchestrator: inject a `Mock` `regime_analyzer` returning
    `RegimeResult(BEARISH,…,emit_signals=False)` → empty `ranked_tickers`, assert
    `scoring_engine.calculate_enhanced_score` **not called**; BULLISH with a ticker scoring in [65,75)
    proves threshold 65 (not 75) is applied.
  - **IT-2** indicators → hard filters → scoring: per-ticker fixture with one failing-H + one passing
    ticker → failing excluded, passing scored.
  - **IT-3** two-pass RS percentile ranks leaders above laggards across a multi-ticker scan.
  - **IT-4** full `POST /api/v1/scan` (reuse `test_endpoints_integration.py` fixtures, not
    `test_scan_endpoint.py`): valid `ScanResponse`; **assert the HTTP-level fork** — all-hard-filter-fail
    → `200` + `ranked_tickers==[]` (not 500); all-fetch-errored → `500`/ScanError. **Also update the
    existing `test_scan_endpoint_with_mocked_api_client` fixture to ≥252 bars** (it will otherwise break
    under V3 — flag, don't treat as unrelated regression).
  - **IT-5** `/api/v1/backtest/single` + `/rolling`: ⚠️ patch **`api.backtest_endpoints.RestApiClient`**
    and `api.backtest_endpoints.config` (the backtest engine builds its OWN client — the
    `api.endpoints.RestApiClient` patch won't intercept it); mock must return ≥252 historical bars **plus
    `horizon_days` forward bars**; for March-2026 the mocked `"SPY"` series must be bearish (declining,
    last-5 below SMA200) → regime-aware predicted-bullish → **0 predicted-bullish** in the matrix.
  - **Definition of done:** all integration tests pass.
  - _Requirements: R1, R2, R5, R7 (component interactions)_

- [ ] 4.4 Run validation suite V1–V4
  - **V1 in-sample** (2024-04-15, 2024-08-01, 2024-11-15, 2025-02-01, 2025-05-01; 108 tickers) →
    Precision ≥85%, portfolio >+3%.
  - **V2 March 2026** (2026-03-01, Top 50) → **0 BUYs** (else inspect SPY vs SMA200).
  - **V3 out-of-sample** (2024-03-01, 2024-07-01, 2024-10-15, 2025-04-01, 2025-06-01; 108 tickers) →
    Precision ≥80%.
  - **V4 portfolio sim** ($10k/BUY, 30-day hold) → win rate ≥70%, R:R ≥2:1.
  - **Record** precision/recall/portfolio per period. If OOS precision <75%, simplify (anti-overfit).
  - _Requirements: R1–R7 (validated end-to-end)_

- [ ] 4.5 Full backend regression + success criteria
  - Run all backend tests (`pytest`). Assert success criteria: in-sample ≥85%, OOS ≥80%, March-2026
    0 BUYs, positive in 4/5 periods, no single trade < −10%, all 200+ tests pass/updated.
  - Ask the user before finalizing if any criterion misses.
  - _Requirements: Success Criteria §6 of requirement.md_

- [ ] 4.6 Comprehensive halal-universe backtest + optimal threshold/score report
  - **Goal:** reproduce the V2 backtesting workflow for the V3 engine — a large multi-date, multi-stock
    backtest that sweeps score/gain thresholds to find the optimal operating point and emits an HTML
    report. (Mirrors V2's `backend/generate_report.py` → `backtest_report.html` and
    `backend/error_analysis.py`.)
  - **Universe:** run the **full halal list (hundreds of tickers)** from `ALL_HALAL_STOCKS.txt` /
    `halal_stocks_usa.md` (371 entries), not just the 108-ticker subset. Batch to respect the 5-concurrent
    Polygon limit; cache per scan.
  - **Dates:** cover **many dates across regimes** — at minimum the in-sample 5 (V1), the out-of-sample 5
    (V3), the bearish March-2026 control, plus additional bull/bear/neutral months; ideally use the
    rolling backtest (`/api/v1/backtest/rolling`, monthly) over 2024–2026.
  - **Threshold/score optimization (V2-style sweep):** for each date/period, sweep the **score
    threshold** (e.g. 50→90 step 5) and the **gain threshold** (e.g. 3%→10%) and tabulate
    Precision / Recall / F1 / portfolio return per combination; identify the **optimal** operating point.
    ⚠️ **anti-overfit:** find the optimum on **in-sample** dates only, then **report its out-of-sample
    performance** — do not pick the threshold that maximizes OOS. Confirm V3's regime thresholds (65
    BULLISH / 75 NEUTRAL) sit near the in-sample optimum; flag if they don't.
  - **Implement:** update `backend/generate_report.py` to be **V3 regime-aware** (it currently hardcodes
    `SCORE_THRESHOLD=50`, `GAIN_THRESHOLD=5` and a fixed 5-date/108-ticker set) — parameterize the
    universe, dates, and sweep ranges; reuse the `/backtest/single` + `/rolling` endpoints. Generate a
    refreshed **`backtest_report.html`** with: per-period confusion matrix (TP/FP/FN/TN),
    accuracy/precision/recall/F1, portfolio P&L, the threshold×gain heatmap, the optimal point, and an
    in-sample-vs-out-of-sample comparison. Optionally extend `error_analysis.py` for per-date TP/FP/FN/TN
    drill-down.
  - **Tests:** unit-test the sweep/aggregation math (confusion-matrix counts, precision/recall/F1,
    optimal-point selection) on synthetic trade sets — `tests/backtest/test_report.py`; do not depend on
    live data for the math.
  - **Deliverable:** the regenerated `backtest_report.html` + a short written summary of the recommended
    score/gain thresholds and the in-sample/out-of-sample metrics. Share with the user for review.
  - **Definition of done:** report generated, sweep math unit-tested, optimal thresholds documented.
  - _Requirements: V1, V3, V4 + Success Criteria §6 (validated at scale); Anti-overfitting §4_

### Phase 5 — Playwright Feature / E2E Testing (FINAL COMPLETION GATE)

> ⛔ **No task in Phases 1–4 is considered fully complete until this phase passes.** Extensive Playwright
> feature testing is the final gate. Capture screenshots to `frontend/test-results/screenshots/`.
>
> ⚠️ **Reality checks (from spec review) — do NOT assume the current setup works:**
> - **`playwright.config.ts` does NOT auto-start the backend today** — its `webServer` only runs `vite`.
>   Task 5.1 must fix this.
> - **The Live Scanner sends only tickers (no `as_of_date`)** → regime is *live/current* and cannot be
>   forced bearish deterministically. Force determinism via the **Backtest tab (fixed past date)** or
>   **`page.route('**/api/v1/scan', …)` fixtures**, not live data.
> - **UI copy:** `MarketRegimeBadge` renders **"Bearish Market"** (Cloudscape `StatusIndicator
>   type="error"`); there is **no** "no signals in bearish market" string and **no** backtest 0-trades
>   empty state (BacktestPanel hides everything when `trades.length === 0`). Assert real strings, or have
>   the implementer add the empty-state copy first.
> - Components have **no `data-testid`s**; existing specs rely on fragile Cloudscape hashed classes.

- [ ] 5.1 E2E prerequisites (config + stable selectors + empty states)
  - **Fix `frontend/playwright.config.ts`:** make `webServer` an **array** that also starts the backend —
    `{ command: 'cd ../backend && uvicorn main:app --port 8000', url: '.../api/v1/health',
    reuseExistingServer: !CI, env: { POLYGON_TOKEN } }` plus the existing vite entry.
  - **Add `data-testid`s** to `MarketRegimeBadge`, the results empty-state, `BacktestPanel`
    confusion-matrix cells + metric cards (Accuracy/Precision/Recall/F1) + the two sliders, so V3 specs
    assert on stable selectors.
  - **Add empty-state copy:** a bearish/zero-candidates message in `ResultsTable`/`App`, and a
    "0 trades / no signals" message in `BacktestPanel` (currently renders nothing at 0 trades). Depends
    on tasks 1.2/1.3 (backend must return empty-valid, not a 500 error).
  - _Requirements: R1, R7 (UI surfacing)_

- [ ] 5.2 Author V3 feature specs in `frontend/tests/e2e/`
  - **`v3-bearish-regime.spec.ts`** — **deterministic via route-mock OR backtest tab**: stub
    `/api/v1/scan` (or run backtest at a known bearish date) → assert **"Bearish Market"** badge +
    empty-state message (added in 5.1), NOT a red error. Screenshots: badge, empty state.
  - **`v3-hard-filters.spec.ts`** — **route-mock** a `ScanResponse` with known weak+strong tickers →
    assert weak (below-MA) absent, leaders present, ranked descending by score; every shown ticker has a
    green SMA50 `SignalBadge` and `score >= threshold`. (Don't hard-code live ticker names.)
  - **`v3-backtest-metrics.spec.ts`** — click the **Backtest tab** first; run a single-date backtest;
    assert confusion matrix + Precision/Recall/F1 cards render; drive sliders via **keyboard**
    (`thumb.press('ArrowRight')`, not `.fill()`) and assert a metric card's text **changes** (structural,
    not a hard-coded %). Preset = Cloudscape `Select` (click-open-then-option); date via inner
    `input[placeholder="YYYY-MM-DD"]`.
  - **`v3-march-2026.spec.ts`** — Backtest tab, date `2026-03-01`, Top 50 preset → assert the
    backtest emits **no qualifying (★) trades**: either the 0-trades empty state (5.1) or a confusion
    matrix with TP=0 and FP=0. (Reworded from "0 BUY signals" — the UI has no "BUY" label.)
  - **`v3-regression.spec.ts`** — core happy-path with V3 active, asserting **V3 invariants** (regime
    badge present; every shown ticker `score >= threshold`) rather than re-running happy-path verbatim
    (avoids duplicating `happy-path`/`comprehensive-test`).
  - _Requirements: R1–R7 (validated through the UI)_

- [ ] 5.3 Run full E2E suite + verify
  - Ensure backend is reachable (now auto-started by 5.1) with `POLYGON_TOKEN` set; prefer `page.route`
    fixtures for regime/hard-filter determinism, reserve live Polygon hits for the fixed-date
    `v3-march-2026` and `v3-regression`.
  - Run `npx playwright test` (existing 5 specs + 5 V3 specs). All pass, 0 failures; screenshots
    generated; `npx playwright show-report` clean.
  - **Definition of done (whole project):** unit + integration + backtest validation + backend regression
    + **all Playwright feature tests green**. Only then mark V3 complete.
  - _Requirements: R1–R7 (validated through the UI)_

---

## Notes

- **Definition of Done (per task):** implementation + **detailed unit tests (mandatory — no unit tests =
  not done)** + referenced property tests + >80% coverage.
- **Definition of Done (whole project):** all per-task unit tests + integration tests (4.3) + backtest
  validation V1–V4 (4.4) + backend regression (4.5) + **comprehensive halal-universe backtest report
  with optimal thresholds (4.6)** + **all Playwright feature tests green (5.3)**.
- **Requirement coverage:** R1→1.1,1.2,1.3,1.4,4.1 · R2→2.2 · R3→2.3 · R4→2.4 · R5→3.1 · R6→3.2 ·
  R7→1.3,4.1,4.2 · R8→2.1 · R9→1.1,2.1 · R10→1.1,2.1.
- **Property coverage:** P1→1.4 · P2→2.2 · P3→2.3 · P4→2.4 · P5→3.1 · P6→3.2 · P7→4.1 · P8→4.1 ·
  P9→2.1 · P10→2.1.
- **Open questions to resolve during impl:** OQ-1 (fetch history ≥252 bars), OQ-2 (surface gate results
  on `TickerScore`?), OQ-3 (EMA21 role in gate) — see design.md §8.
- **Backward compatibility:** `RegimeResult` return type + recovery removal require updating
  `test_regime_analyzer.py` and `test_scoring_engine.py` (see design.md §7).

---

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["1.2", "2.2"] },
    { "id": 2, "tasks": ["1.3", "2.3", "2.4"] },
    { "id": 3, "tasks": ["1.4", "2.5"] },
    { "id": 4, "tasks": ["3.1"] },
    { "id": 5, "tasks": ["3.2"] },
    { "id": 6, "tasks": ["4.1"] },
    { "id": 7, "tasks": ["4.2"] },
    { "id": 8, "tasks": ["4.3"] },
    { "id": 9, "tasks": ["4.4"] },
    { "id": 10, "tasks": ["4.5"] },
    { "id": 11, "tasks": ["4.6"] },
    { "id": 12, "tasks": ["5.1"] },
    { "id": 13, "tasks": ["5.2"] },
    { "id": 14, "tasks": ["5.3"] }
  ]
}
```
