# Trade Engine — Requirements

> **Source:** Brainstorm + validated prototype (`backend/scripts/trade_plan_proto.py`), which showed a
> positive edge (+0.27R/trade, 41% target-before-stop on a 2:1 plan) on real Massive data.
>
> **Goal:** For each **bullish BUY candidate** the scanner surfaces, produce a concrete, equity-only
> **trade plan** — entry, volatility-based stop, profit targets, reward:risk, the realistic 30-day
> expected move, an earnings-in-window warning, and a calibrated probability of hitting target. No
> options/futures are ever traded — options data is used only as a (better) volatility input.
>
> Requirement IDs: **R1–R12**. Validation: **V1–V3**. Referenced by `design.md` (properties P1–Pn) and
> `task.md` (`_Requirements:_`).

## 1. Context

The V3 scanner says "this stock is bullish over the next 30 days." It does **not** say *how far* it might
go, *where to get out*, or *whether the risk/reward is worth it*. The Trade Engine answers those — turning
a signal into an actionable, risk-defined plan with honest, probabilistic targets (a range + probability,
never a single magic number).

**Philosophy:** every number must be **computed from data and back-tested for calibration** — if we claim
"60% chance of +5%," the backtest must show it actually happened ~60% of the time, or we don't ship it.

## 2. Functional Requirements

### R1 — Volatility-based stop (ATR)
**Files:** `core/trade_engine.py`

Stop = `entry − atr_mult × ATR(14)`, with `atr_mult` configurable (default **2.0**; prototype used 1.5,
2.0–2.5 to be tuned). Cap the maximum loss at a hard floor (default **−10%**) so a high-ATR name can't
imply a catastrophic stop. `risk_per_share = entry − stop` must be **> 0**.

### R2 — Profit targets (R-multiples)
`target1 = entry + 2.0 × risk` (primary), `target2 = entry + 3.0 × risk` (stretch). Both multiples
configurable. Report each as an absolute price **and** a % from entry.

### R3 — Expected 30-day move (volatility)
Compute the realistic 1σ move over the horizon. **Baseline:** historical daily-return σ (or ATR),
scaled by √(horizon_trading_days). **Enhancement (R8):** options-implied volatility when available.
Record which source was used (`vol_source: "options_iv" | "historical"`). Used to (a) sanity-check
targets and (b) widen for earnings (R6).

### R4 — Resistance cap / annotation
Compute nearest overhead resistance = max(recent 60-day swing high, 52-week high). If `target1` sits
**above** resistance, annotate it (`target_above_resistance: true`) — a target beyond resistance is less
likely to be reached cleanly. Do **not** silently move the target; surface the tension.

### R5 — Reward:Risk and minimum quality gate
`reward_risk = (target1 − entry) / risk`. A plan is "actionable" only when `reward_risk >=`
`MIN_REWARD_RISK` (default **1.5**). Plans below are still shown but flagged `low_rr: true`.

### R6 — Earnings-in-window flag → widen target  *(user decision)*
Query Massive Benzinga earnings (R10). If an earnings date falls within the horizon:
- set `earnings_in_window: "<YYYY-MM-DD>"`,
- **widen** the target band (raise `target2`/`expected_move` by an `EARNINGS_WIDEN_FACTOR`, default
  **1.5×**) and **lower the confidence** (R7),
- the UI shows a clear **"Earnings on <date>"** warning.
Earnings are NOT predicted — they are flagged as elevated, two-sided risk. (Stock is **not** excluded.)

### R7 — Probability of hitting target (calibrated)
`prob_hit_target1` = empirical probability, from the backtest, that a plan of this **setup bucket**
(e.g. score band, ATR band) reached target1 before stop. Sourced from a calibration table built in V1/V3,
not invented. Reduced when `earnings_in_window` (R6).

### R8 — Options-implied expected move (enhancement, equity-only)
If Massive's option-chain snapshot exposes implied volatility (or usable ATM option prices), derive the
market's expected move and use it for R3 instead of historical σ. **Fallback:** if options data is
missing/illiquid/invalid for a ticker, silently use historical σ. Never block a plan on options.

### R9 — Analyst consensus target (anchor, optional)
If Massive Benzinga consensus is available, attach `analyst_target` (mean) + `analyst_low/high` as an
external sanity anchor shown alongside our target. Treated skeptically; never overrides our computed plan.

### R10 — Massive data access for earnings / options / analyst
**Files:** `core/api_client.py` (or new `core/massive_data.py`)

Add a thin client for the non-aggregate Massive REST endpoints used above:
`/rest/partners/benzinga/earnings`, `/rest/options/snapshots/option-chain-snapshot`,
`/rest/partners/benzinga/consensus-ratings`. Same auth as the existing aggregates client.
🛑 **First task must verify** the Massive REST base URL, auth, and each response schema (via the Massive
MCP `get_endpoint_docs` / `call_api`) — these are unconfirmed.

### R11 — Only for candidates; surfaced everywhere
Trade plans are computed only for **BUY candidates** (passed hard filters AND score ≥ regime threshold) —
not for every scanned ticker (cost). Surfaced on `TickerScore.trade_plan`, in the results table
(expandable per stock), and in the downloadable scan report.

### R12 — OHLC data availability
**Files:** `core/models.py`, `core/api_client.py`

ATR, swing highs/lows and resistance need **high/low** data. Extend `StockData` to carry `highs`/`lows`
(populated from the same fetch the scanner already does — no extra API call), or have the engine reuse
the range fetch. No new round-trips per ticker for the core plan.

## 3. Validation Requirements

### V1 — Calibration backtest (the gate)
Over the in-sample dates × halal universe, build a plan for every historical BUY candidate, walk forward
30 trading days bar-by-bar (path-dependent first-touch of stop vs target), and measure:
- **target1-before-stop rate** (must clear the breakeven implied by R:R — e.g. >33% for 2:1),
- **expectancy in R** (must be **> 0**),
- **coverage**: realized 30-day high lands in the predicted band ≈ as often as `prob_hit_target1` claims
  (within tolerance). Build the calibration table used by R7 here.

### V2 — ATR-multiple / target-multiple sweep
Sweep `atr_mult` (1.5–3.0) and target multiples to pick the operating point with the best expectancy on
**in-sample**, report it on **out-of-sample** (anti-overfit, same discipline as V3).

### V3 — Earnings-window subset
Show the win/expectancy difference for plans **with** vs **without** earnings in the window — confirms the
earnings flag (R6) is capturing real, elevated variance.

## 4. Success Criteria
1. Positive expectancy (**> 0R**) on in-sample AND out-of-sample candidate plans.
2. Probability claims calibrated within tolerance (coverage check, V1).
3. Earnings-in-window plans correctly flagged + widened (V3 shows higher variance there).
4. Every plan reproducible from data — no hand-set or hallucinated numbers.
5. Plans render in the table + report; all existing tests stay green.

## 5. Out of Scope (for now)
Options trading, real-money order placement, intraday/stop-trailing management, position sizing by account
equity (could be a later add), multi-leg strategies.
