# Trade Engine — Implementation Plan

> Implements `design.md` / `requirement.md`. House TDD format: checkbox tasks with implementation steps,
> mandatory unit tests, property refs, and `_Requirements: Rn_` traceability. Dependency waves at the end.
>
> **Mandate:** every task ships with unit tests; no task is "done" without them. Massive-dependent tasks
> degrade gracefully (fallbacks) and are gated behind the schema verification in 1.1. Calibration (Phase 4)
> is the ship-gate: no probability/target claim goes to the UI until coverage is verified.

## Phase 0 — Verify the unknowns (do FIRST)

- [ ] 0.1 Confirm Massive REST access for the new endpoints (OQ-1, OQ-2)
  - Using the Massive MCP (`get_endpoint_docs`, `call_api`), confirm for **earnings**, **option-chain
    snapshot**, **consensus-ratings**: the exact REST base URL, the auth (header vs `apiKey` param), and a
    sample JSON response shape. Record whether the **option snapshot contains `implied_volatility`** (OQ-2).
  - Write findings into `design.md` §3.2 / §7 (resolve OQ-1, OQ-2). Capture one sample payload per endpoint
    in the test fixtures dir.
  - **Done:** base URL + auth + 3 response schemas documented; IV-availability decided (use IV vs straddle
    vs BS-inversion vs historical-only).
  - _Requirements: R8, R9, R10_

## Phase 1 — Data layer

- [ ] 1.1 Add OHLC to `StockData` (R12)
  - **Implement (`core/models.py`, `core/api_client.py`):** add `highs`, `lows` (Optional[np.ndarray]) to
    `StockData`; populate from the bars already parsed in `fetch_stock_data` (h/l currently dropped). No new
    request.
  - **Unit tests (`tests/unit/test_api_client.py`):** highs/lows populated, same length as closes; older
    code paths still work with them None.
  - **Property P9 (precondition):** ATR needs highs/lows present.
  - _Requirements: R12_

## Phase 2 — Core TradeEngine (the validated prototype, productionised)

- [ ] 2.1 `TradeConfig` + `TradeEngine.atr()` (R1, R3)
  - **Implement (`config.py`, `core/trade_engine.py`):** `TradeConfig` defaults (atr_mult 2.0,
    max_loss_pct 0.10, target1_R 2.0, target2_R 3.0, min_reward_risk 1.5, earnings_widen 1.5, sigma_n 20,
    resistance_lookback 60); `atr(highs,lows,closes,n=14)` (true-range mean).
  - **Unit tests:** ATR on known OHLC; insufficient bars handled.
  - **Property P9: ATR = mean of last N true ranges.** _Requirements: R1, R3_

- [ ] 2.2 `build_plan` — stop, targets, expected move, R:R (R1, R2, R3, R5)
  - **Implement:** stop = max(entry − atr_mult·ATR, entry·(1−max_loss_pct)); risk; target1/target2 =
    entry + R·risk; expected_move = σ_daily·√horizon (historical branch); reward_risk; low_rr flag.
  - **Unit tests:** stop < entry & risk>0 always; stop cap at −max_loss_pct; target multiples exact;
    reward_risk == target1_R; low_rr threshold; expected_move formula.
  - **Properties P1, P2, P4, P9.** _Requirements: R1, R2, R3, R5_

- [ ] 2.3 Resistance cap/annotation (R4)
  - **Implement:** resistance = max(60-day high, 52-week high); set `target_above_resistance`; never mutate
    target.
  - **Unit tests:** flag true iff target1 > resistance; target unchanged.
  - **Property P3.** _Requirements: R4_

## Phase 3 — Massive enhancements (graceful)

- [ ] 3.1 `MassiveDataClient` (R10) — `core/massive_data.py`
  - **Implement:** `earnings()`, `consensus()`, `option_expected_move()` per the schemas verified in 0.1;
    same auth as `RestApiClient`. Each returns `None`/`[]` on missing data — never raises.
  - **Unit tests (mocked HTTP):** parse a sample earnings/consensus/option payload; missing-data → None;
    network error → None (logged).
  - **Property P6 (precondition).** _Requirements: R8, R9, R10_

- [ ] 3.2 Earnings-in-window flag + widen (R6)  *(user decision)*
  - **Implement (`trade_engine.build_plan`):** accept `earnings_date`; if within horizon → set
    `earnings_in_window`, widen target2/expected_move by `earnings_widen`, and ensure `prob_hit_target1` is
    not increased.
  - **Unit tests:** earnings inside window widens; outside window no-op; prob not raised.
  - **Property P5.** _Requirements: R6_

- [ ] 3.3 Options-implied expected move (R8) + analyst anchor (R9)
  - **Implement:** when `options_move` supplied & valid → `expected_move` uses it, `vol_source="options_iv"`;
    else historical, `vol_source="historical"`. Attach analyst_target/low/high when present.
  - **Unit tests:** options override vs fallback; None options → historical, no raise; analyst fields pass
    through.
  - **Property P6.** _Requirements: R8, R9_

## Phase 4 — Calibration backtest (SHIP GATE — V1, V2, V3)

- [ ] 4.1 `scripts/trade_backtest.py` — first-touch walk-forward
  - **Implement:** for historical BUY candidates, build plan, walk forward 30 trading bars bar-by-bar;
    record first-touch (stop vs target1 vs target2), realized R; aggregate target-before-stop %, expectancy.
    (Generalises the prototype `trade_plan_proto.py`.)
  - **Unit tests:** the first-touch evaluator on synthetic forward bars (stop-first, target-first, neither).
  - _Requirements: V1_

- [ ] 4.2 Calibration table (R7) — `core/trade_calibration.py` + `data/trade_calibration.json`
  - **Implement:** bucket candidates (score band × ATR/vol band [× earnings flag]); compute empirical
    P(target1 before stop) per bucket; serialise to JSON; `CalibrationTable.lookup(bucket)` loads it; missing
    bucket → None. Wire into `build_plan` so `prob_hit_target1` is set from the table.
  - **Unit tests:** lookup returns the stored prob; unknown bucket → None; build_plan uses it (P7).
  - **Property P7.** _Requirements: R7_

- [ ] 4.3 Run V1–V3 + sweep, document results
  - **V1** in-sample + out-of-sample: expectancy **> 0R**, coverage of prob claims within tolerance.
  - **V2** sweep atr_mult (1.5–3.0)/target multiples on in-sample; report best on OOS.
  - **V3** earnings-window subset: higher variance confirmed.
  - **Done:** write `docs/TRADE_ENGINE_RESULTS.md`; only proceed to UI if expectancy > 0 and calibrated.
  - _Requirements: V1, V2, V3, Success Criteria_

## Phase 5 — API + orchestrator

- [ ] 5.1 `TradePlan` Pydantic model + `TickerScore.trade_plan` (R11)
  - **Implement (`api/models.py`):** `TradePlan` model; optional `trade_plan` on `TickerScore`.
  - **Unit tests:** serialises/deserialises; default None.
  - _Requirements: R11_

- [ ] 5.2 Orchestrator wiring (R11) — candidate-only, batched Massive
  - **Implement (`core/orchestrator.py`):** for candidates (or full-scores in backtest mode), build plans;
    batch-fetch earnings/consensus/options for the candidate set; attach `trade_plan`. Skip on missing data.
  - **Unit tests (`tests/unit/test_orchestrator.py`):** plan present for candidate, None for hard-filter
    fail (P8); no Massive call when no candidates.
  - **Property P8.** _Requirements: R11_

## Phase 6 — Frontend

- [ ] 6.1 Types + trade-plan UI (R11)
  - **Implement (`types/scan.ts`, `components/ResultsTable.tsx`):** `trade_plan?` type; an expandable
    "Trade Plan" view per stock (entry/stop/target1/target2, R:R, expected move, resistance flag,
    **"⚠ Earnings on <date>"** badge, prob%, analyst range). data-testids for e2e.
  - **Tests:** vitest render; tsc/eslint clean.
  - _Requirements: R11_

- [ ] 6.2 Download report — Trade Plan section (R11)
  - **Implement (`utils/scanReport.ts`):** add trade-plan columns/section to the HTML report.
  - **Tests:** e2e download asserts plan fields + earnings badge present.
  - _Requirements: R11_

## Phase 7 — Validation gate

- [ ] 7.1 Full regression + e2e
  - Backend `pytest` (all green, incl. new unit/property), `ruff` clean; frontend lint/tsc/unit; Playwright
    e2e (route-mocked trade plan: expander, earnings badge, sorting unaffected). Confirm Success Criteria.
  - _Requirements: Success Criteria_

## Notes
- **Definition of Done (per task):** implementation + unit tests + referenced property + >80% coverage.
- **Ship gate:** Phase 4 (calibration) must pass — positive expectancy + calibrated probabilities — before
  Phase 6 exposes anything to users. No hallucinated numbers reach the UI.
- **Property coverage:** P1→2.2 · P2→2.2 · P3→2.3 · P4→2.2 · P5→3.2 · P6→3.1,3.3 · P7→4.2 · P8→5.2 · P9→2.1,2.2.
- **Open questions:** OQ-1/OQ-2 resolved in 0.1; OQ-3 (bucket granularity) in 4.2.

## Task Dependency Graph
```json
{
  "waves": [
    { "id": 0, "tasks": ["0.1"] },
    { "id": 1, "tasks": ["1.1"] },
    { "id": 2, "tasks": ["2.1"] },
    { "id": 3, "tasks": ["2.2", "2.3"] },
    { "id": 4, "tasks": ["3.1"] },
    { "id": 5, "tasks": ["3.2", "3.3"] },
    { "id": 6, "tasks": ["4.1"] },
    { "id": 7, "tasks": ["4.2"] },
    { "id": 8, "tasks": ["4.3"] },
    { "id": 9, "tasks": ["5.1"] },
    { "id": 10, "tasks": ["5.2"] },
    { "id": 11, "tasks": ["6.1", "6.2"] },
    { "id": 12, "tasks": ["7.1"] }
  ]
}
```
