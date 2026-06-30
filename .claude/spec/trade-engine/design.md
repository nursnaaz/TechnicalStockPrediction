# Trade Engine — Design

> Implements `requirement.md` (R1–R12, V1–V3). Mirrors the house spec style (component specs + numbered
> Correctness Properties tagged `Validates: Rn`). Scoped to the trade-plan delta on top of the V3 scanner.

## 1. Overview

A new `TradeEngine` turns each BUY candidate into a risk-defined equity plan. It is **pure + deterministic**
given its inputs (OHLC + optional earnings/options/analyst data), so it is fully unit-testable and
back-testable. Two data tiers:

- **Core (always available, from OHLC):** ATR stop, R-multiple targets, historical expected move,
  resistance cap, reward:risk. This is the validated prototype.
- **Enhancements (Massive, degrade gracefully):** earnings-in-window flag (+widen), options-implied
  expected move, analyst consensus anchor. Any missing/invalid → fall back, never block.

## 2. Architecture / data flow

```
ScanOrchestrator (PASS 2, per BUY candidate only — R11)
   │  has: OHLC history (R12), score, regime
   ▼
TradeEngine.build_plan(entry, highs, lows, closes, horizon, cfg, *, earnings=None, options=None, analyst=None)
   ├── ATR(14), historical σ                       → stop (R1), expected_move (R3)
   ├── target1=2R, target2=3R                       → (R2), reward_risk (R5)
   ├── resistance = max(60d high, 52wk high)        → cap/annotate (R4)
   ├── if options.iv usable → expected_move override (R8) else historical
   ├── if earnings in window → widen + flag (R6), lower prob
   ├── prob_hit_target1 = CalibrationTable.lookup(bucket)   (R7)
   └── analyst fields if present                     (R9)
   ▼  TradePlan dataclass → TickerScore.trade_plan (R11)
```

**Where Massive enhancement data is fetched:** in the orchestrator, *after* candidates are known (so we
only pay for ~8–25 names, not the whole universe). Batched calls to `MassiveDataClient` (R10) for
earnings/analyst; options snapshot only for names that pass a liquidity check.

## 3. Component specifications

### 3.1 Data layer — OHLC (R12)
`StockData` (`core/models.py`) gains optional `highs: np.ndarray | None`, `lows: np.ndarray | None`.
`RestApiClient.fetch_stock_data` already parses `h`/`l` per bar — populate them (currently dropped). No new
request. Indicator/scoring code ignores the new fields (backward-compatible).

### 3.2 MassiveDataClient (R10) — `core/massive_data.py`
```python
class MassiveDataClient:
    def __init__(self, api_key, base_url): ...
    async def earnings(self, ticker, from_date, to_date) -> list[dict]      # benzinga/earnings
    async def consensus(self, ticker) -> dict | None                         # benzinga/consensus-ratings
    async def option_expected_move(self, ticker, as_of, horizon_days) -> float | None  # chain snapshot
```
🛑 **Unconfirmed and verified in task 1.1:** exact REST base URL, auth header/param, and JSON shapes.
`option_expected_move` reads ATM implied volatility from the chain snapshot if present; if the snapshot has
no IV, it falls back to ATM straddle mid / Black-Scholes inversion; if neither is usable → returns `None`.

### 3.3 TradeEngine (R1–R9) — `core/trade_engine.py`
```python
@dataclass
class TradePlan:
    entry: float
    stop: float; stop_pct: float
    target1: float; target1_pct: float
    target2: float; target2_pct: float
    risk_per_share: float
    reward_risk: float
    expected_move_pct: float
    vol_source: str                 # "options_iv" | "historical"
    resistance: float; resistance_pct: float
    target_above_resistance: bool
    low_rr: bool
    earnings_in_window: str | None   # date or None
    prob_hit_target1: float | None   # 0..1, calibrated
    analyst_target: float | None
    analyst_low: float | None
    analyst_high: float | None

class TradeEngine:
    def __init__(self, cfg: TradeConfig, calibration: CalibrationTable | None = None): ...
    @staticmethod
    def atr(highs, lows, closes, n=14) -> float: ...
    def build_plan(self, *, entry, highs, lows, closes, horizon=30,
                   earnings_date=None, options_move=None, analyst=None) -> TradePlan: ...
```
`TradeConfig`: `atr_mult=2.0`, `max_loss_pct=0.10`, `target1_R=2.0`, `target2_R=3.0`,
`min_reward_risk=1.5`, `earnings_widen=1.5`, `sigma_n=20`, `resistance_lookback=60`. Lives in `config.py`.

**build_plan logic:** ATR + σ → stop (capped) → risk → targets → expected move (options override) →
resistance flag → earnings widen + prob reduction → R:R + low_rr → CalibrationTable lookup.

### 3.4 CalibrationTable (R7) — `core/trade_calibration.py`
Maps a **setup bucket** (score band × ATR/vol band, optionally earnings flag) → empirical
`P(target1 before stop)`, learned in V1. Serialized to `data/trade_calibration.json` (built by the
calibration script, loaded at startup). Missing bucket → `None` (UI shows "—", not a fake number).

### 3.5 Orchestrator integration (R11)
In PASS 2, for tickers that are candidates (or all hard-filter passers in backtest mode), build a plan and
attach `TickerScore.trade_plan`. Earnings/analyst/options fetched in a batched step for the candidate set.
Skipped entirely when data unavailable (plan stays `None`).

### 3.6 API + UI surfacing (R11)
- `api/models.py`: `TickerScore.trade_plan: TradePlan | None` (Pydantic model mirroring the dataclass).
- Frontend `types/scan.ts`: `trade_plan?` on `TickerScore`.
- `ResultsTable`: an expandable "Trade Plan" row/popover per stock — entry/stop/target1/target2, R:R,
  expected move, resistance flag, **"⚠ Earnings on <date>"** badge, prob%, analyst range.
- `scanReport.ts`: a Trade Plan section/columns in the downloadable HTML report.

## 4. Correctness properties

- **P1** stop < entry and risk > 0 for all inputs; stop never below `entry × (1 − max_loss_pct)`. *(R1)*
- **P2** `target1 = entry + target1_R × risk`; `reward_risk == target1_R` (±ε) before earnings widen. *(R2,R5)*
- **P3** `target_above_resistance` true iff `target1 > resistance`; resistance never silently mutates the
  target. *(R4)*
- **P4** `low_rr` true iff `reward_risk < min_reward_risk`. *(R5)*
- **P5** earnings_in_window set ⇒ `target2`/expected_move strictly widened AND `prob_hit_target1` not
  increased vs the no-earnings case. *(R6)*
- **P6** `vol_source == "options_iv"` iff a valid options move was supplied, else `"historical"`; a `None`
  options move never raises. *(R8,R3)*
- **P7** `prob_hit_target1` comes only from the calibration table or is `None` — never computed ad hoc. *(R7)*
- **P8** trade_plan is populated only for candidates (or in backtest full-scores mode); never for
  hard-filter failures. *(R11)*
- **P9** ATR equals the mean of the last N true ranges; `expected_move_pct == σ_daily·√horizon·100` in the
  historical branch. *(R3)*

## 5. Testing & calibration strategy

- **Unit (pure):** P1–P9 on synthetic OHLC — deterministic, no network. ATR/σ correctness, stop cap,
  target multiples, resistance flag, earnings widen, options override, low_rr.
- **MassiveDataClient:** mocked-HTTP tests for earnings/consensus/options parsing + graceful `None` on
  missing data. One live smoke (gated on token) confirming the verified schema (task 1.1).
- **Calibration backtest (V1–V3):** `scripts/trade_backtest.py` builds plans for historical candidates,
  walks forward bar-by-bar (first-touch), reports target-before-stop %, expectancy R, coverage; writes
  `data/trade_calibration.json`. Sweep (V2) on in-sample, report out-of-sample. Earnings subset (V3).
- **Frontend:** vitest for the trade-plan rendering; Playwright e2e (route-mocked plan) asserting the
  expandable plan + earnings badge + report download.

## 6. Backward compatibility / risk
- New `StockData.highs/lows` and `TickerScore.trade_plan` are optional → no breakage; existing 312 tests
  unaffected.
- **Risk (task 1.1):** Massive REST base/auth/schemas for earnings/options/analyst are unconfirmed —
  verify first; if any endpoint is unavailable, that enhancement degrades to its fallback and the core plan
  still ships.
- **Cost:** plans + Massive calls only for the candidate set (R11), keeping API volume bounded.

## 7. Open questions
- **OQ-1** Massive REST base URL + auth for `/rest/...` endpoints (vs the aggregates base)? Resolve in 1.1.
- **OQ-2** Does the option-chain snapshot include `implied_volatility`? If not, straddle-mid vs BS-inversion
  for the expected move. Resolve in 1.1 / 3.x.
- **OQ-3** Bucketing granularity for the calibration table (score band × ATR band — how many buckets before
  cells get too sparse on ~hundreds of historical trades)?
