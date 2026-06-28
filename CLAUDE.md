# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**TechnicalStockPrediction** — A bullish stock scanner that scores stocks on technical indicators, detects chart patterns, and validates predictions via point-in-time backtesting against historical Polygon.io data. The current engine is **V3**: a precision-first, trend-following scanner for halal-screened US stocks.

Stack: Python FastAPI backend + React/TypeScript/Cloudscape frontend. Data source: Polygon.io REST API (requires `POLYGON_TOKEN` env var set globally in shell — not loaded from a file).

The active development branch is `feature/v3-high-precision`. The V3 design is spec-driven: see `.claude/spec/{requirement,design,task}.md` (requirements R1–R10, design Correctness Properties P1–P10, TDD task list). Keep those in sync when changing engine behavior.

## Commands

### Backend

```bash
cd backend && source .venv/bin/activate

uvicorn main:app --reload --port 8000     # run API (Swagger at /docs)

pytest                                     # all tests (308, must stay green)
pytest tests/unit/test_scoring_engine.py -v   # single file
pytest -m unit | -m property | -m integration # by marker
pytest --cov=. --cov-report=term-missing

# Lint + format (config in backend/pyproject.toml — ruff):
ruff check .            # lint (clean)
ruff format .           # auto-format

# Live-data validation / tuning (run from backend/; need POLYGON_TOKEN; hit Polygon, can be slow):
python scripts/validate_v3.py smoke|v1|march|v3  # precision/recall on fixed date sets
python scripts/tune_v3.py                        # full halal universe x 10 dates -> docs/ reports + CSV
python scripts/tune_v3.py --from-csv             # regenerate reports from docs/V3_tuning_data.csv (no refetch)
python scripts/analyze_fp.py [dates...]          # false-positive misclassification research
```

### Frontend

```bash
cd frontend
npm run dev                                # Vite dev server (:5173)
npx tsc --noEmit                           # type-check
npm test                                   # vitest unit tests (e2e excluded)
npm run lint
npm run build
npx playwright test tests/e2e/v3-*.spec.ts # V3 feature gate (config auto-starts the backend)
```

> Property tests use a Hypothesis profile in `backend/tests/property/conftest.py` that suppresses the
> `data_too_large` health check. `npx playwright test` starts BOTH servers via the `webServer` array in
> `playwright.config.ts`; the e2e specs are excluded from vitest via `vitest.config.ts`.

## Architecture

### Backend pipeline (V3, two-pass)

`ScanOrchestrator.execute_scan(request, as_of_date=None, apply_signal_gate=True)` in `core/orchestrator.py`:

```
1. MarketRegimeAnalyzer.analyze_regime() -> RegimeResult(regime, threshold, emit_signals)
     BEARISH (and apply_signal_gate) -> short-circuit, return zero candidates.
2. PASS 1 (per ticker): fetch (>=252 trading bars) -> IndicatorCalculator.calculate_all() -> raw RS.
3. Compute RS PERCENTILE across the universe (min-rank {value->percentile} map).
4. PASS 2 (per ticker): ScoringEngine.passes_hard_filters() gate -> calculate_enhanced_score(rs_percentile)
     -> keep only score >= regime.threshold (when apply_signal_gate).
5. RankingService.rank_tickers() -> ScanResponse; ScanStore persists to SQLite.
```

Key invariants:
- **`apply_signal_gate=False`** (used by backtesting) skips the bearish short-circuit AND the threshold
  filter, returning ALL hard-filter-passing scored tickers + the regime — needed to compute FN/TN and to
  sweep thresholds. Production/UI uses the default `True` (candidates only).
- **Empty result is valid**: all-filtered-out → HTTP 200 + empty `ranked_tickers`. Only all-fetches-errored
  raises `ScanError` (500). Don't reinstate a blanket "all tickers failed" guard.
- Hard-filter exclusions and below-threshold tickers are `continue`d, NOT counted as fetch errors.

`config.py` constants that matter: `HISTORY_FETCH_DAYS=400` (calendar days — Polygon `days` is calendar,
~250 trading bars per 365; 400 guarantees ≥`MIN_TRADING_BARS=252`), `BULLISH_SCORE_THRESHOLD=65`,
`NEUTRAL_SCORE_THRESHOLD=75`, `REGIME_PERSISTENCE_DAYS=5`.

### Regime gate (`core/regime_analyzer.py`)

Returns a `RegimeResult` dataclass (not a bare enum). Gate = SPY vs its 200-day SMA with 5-day
persistence: all last-5 closes above → BULLISH (threshold 65, emit); all below → BEARISH (emit_signals
False); otherwise NEUTRAL (threshold 75, emit). EMA21 is computed for context only. Falls back to NEUTRAL
on insufficient history or API error. **Changing the return type ripples into `orchestrator.py` and
`backtest/engine.py`.**

### Indicators (`core/indicator_calculator.py`, `core/models.py`)

`calculate_all()` populates `TechnicalIndicators`: sma_50/150/200, **sma_200_slope** (20-bar, via
`sma_slope()`), **week52_high/low** (from `prices[-252:]`), ema_20/9, MACD (line/signal/hist),
avg_volume_20, relative_strength (raw), rsi_14, roc_10, proximity_to_20d_high. All fields `Optional[float]`
(None when history insufficient → that hard-filter check fails conservatively).

### Scoring engine (V3) — `core/scoring_engine.py`

- **`passes_hard_filters(price, indicators) -> (bool, {H1..H6})`** — Minervini gate, ANY fail → exclude:
  H1 price>SMA200, H2 SMA200 slope>0, H3 price>SMA150, H4 SMA50>SMA200, H5 price≥1.30×52w-low,
  H6 price≥0.75×52w-high. Missing indicator fails its check.
- **`calculate_score(price, volume, indicators, rs_percentile=None)`** components (final clamped to [0,100]):

  | Component | Range | Notes |
  |---|---|---|
  | Trend (SMA50+EMA20) | 0–20 | gradient |
  | Extension penalty | 0 to −25 | dist>SMA50 + RSI overbought + ROC-fading divergence |
  | **Climax penalty** | 0 to −12 | at-high(prox≥98) + RSI≥68 + extended≥8% (precision fix — don't chase tops) |
  | Momentum (MACD+ROC) | 0–20 | |
  | Strength (RSI + **RS percentile**) | 0–20 | percentile tiers ≥90→10/≥70→7/≥50→4; raw-RS fallback if None |
  | Confirmation (Volume+Breakout) | 0–20 | |
  | **Divergence penalty** | 0 to −8 | `divergence_penalty()`: agreement of {RSI>50,MACD>sig,ROC>0,price>SMA50}; <0.6→−8, ≤0.75→−4 |

- **`calculate_enhanced_score(..., rs_percentile=None)`** adds Stage 2 (0–10) + Pattern (0–10) via
  `StageClassifier` / `PatternDetector`.
- The V2 **recovery bonus is removed** (V3 never bottom-fishes). Don't reintroduce points for below-MA stocks.

### Backtesting (`backend/backtest/`)

`BacktestEngine` calls `execute_scan(apply_signal_gate=False)` for full-universe scores, then
`_analyze_trade(..., regime_tradeable, bullish_threshold)` sets **regime-aware** predicted-bullish:
`regime != BEARISH AND score >= regime threshold` (bearish dates → 0 BUYs). `metrics.py` = confusion
matrix / precision / recall / F1. Endpoints: `POST /api/v1/backtest/single` and `/rolling`. The frontend
`BacktestPanel` re-buckets the confusion matrix client-side from each trade's `score` + `max_gain_pct`
(score/gain sliders), so the backtest just returns all trades.

### Frontend (`frontend/src/`)

`App.tsx` (Live Scanner + Backtest tabs) → `components/` (Cloudscape): `BacktestPanel`, `ResultsTable`
(regime-aware empty state), `MarketRegimeBadge`, `SignalBadges`, etc. Services in `services/*.ts`, types in
`types/*.ts`. V3 added `data-testid`s (e.g. `market-regime-badge`, `results-empty`, `metric-precision`,
`cm-tp/fp/fn/tn`, `*-threshold-slider`) for the Playwright specs in `tests/e2e/v3-*.spec.ts` (route-mocked
for determinism — live regime/data is non-deterministic).

## Reference reports & data (repo root)

- `docs/V3_VALIDATION_RESULTS.md` — in/out-of-sample precision (in-sample ~81.5%, OOS ~56.7%, recall ~33–35%).
- `docs/V3_TUNING_REPORT.html` — presentable: precision heatmap (score×gain%), $1k/signal portfolio, per-date
  per-stock breakdown. `docs/V3_TUNING_REPORT.md` is the summary; `docs/V3_tuning_data.csv` is the raw 714-obs data.
- Halal universe: `data/ALL_HALAL_STOCKS.txt` (~212 unique tickers when fully parsed; `tune_v3.load_universe()`
  dedupes it). Other docs (V2/V3 plans, MANIFEST) live under `docs/`.

## Repository layout (post-restructure)

```
backend/   FastAPI app: api/ core/ backtest/ utils/, config.py, main.py
           scripts/  — dev/analysis tools (validate_v3, tune_v3, analyze_fp), run from backend/
           pyproject.toml — ruff (lint+format) + mypy config
frontend/  React + Cloudscape (src/components, services, types; tests/e2e Playwright)
data/      halal ticker lists (ALL_HALAL_STOCKS.txt, …)
docs/      plans + generated reports (V3_TUNING_REPORT.html/md, V3_VALIDATION_RESULTS.md, MANIFEST.md)
.claude/spec/  V3 requirement.md / design.md / task.md
```

**Honest engine reality (don't oversell):** FP and TP trades are statistically near-identical on all
indicators; precision ceilings ~60% at score≥80. The system is net-positive (~+2%/30-day cycle at best
threshold) but with high month-to-month variance. A larger precision jump needs new information
(pullback-based entries, consolidation/VCP tightness, fundamentals), not parameter tuning. Respect the
anti-overfitting rules in `.claude/spec/requirement.md` (e.g. tune on in-sample, report out-of-sample;
OOS<75% precision ⇒ simplify, don't date-tune).

## Tests layout

`backend/tests/{unit,property,integration,backtest}/`, `asyncio_mode = auto`, markers
`unit|property|integration|slow`. Integration tests (`test_v3_pipeline.py`) wire real core components with a
mocked per-ticker `api_client` returning ≥260-bar synthetic data. When changing the regime return type or
scoring, expect to update `test_regime_analyzer.py` / `test_scoring_engine.py` / `test_orchestrator.py`.
