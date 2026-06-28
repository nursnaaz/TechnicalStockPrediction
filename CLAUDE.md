# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**TechnicalStockPrediction** — A bullish stock scanner that scores stocks on technical indicators, detects chart patterns, and validates predictions via backtesting against historical Polygon.io data. Target use case: identifying halal-screened stocks showing bullish technical setups.

Stack: Python FastAPI backend + React/TypeScript/Cloudscape frontend. Data source: Polygon.io REST API (requires `POLYGON_TOKEN` env var set globally in shell).

## Commands

### Backend

```bash
cd backend
source .venv/bin/activate

# Run server (hot-reload)
uvicorn main:app --reload --port 8000

# Run all tests
pytest

# Run a single test file
pytest tests/unit/test_scoring_engine.py -v

# Run by marker
pytest -m unit
pytest -m property
pytest -m integration

# Run with coverage
pytest --cov=. --cov-report=term-missing
```

### Frontend

```bash
cd frontend

# Dev server
npm run dev

# Type-check only (no emit)
npx tsc --noEmit

# Unit tests (vitest)
npm test

# Lint
npm run lint

# Build for production
npm run build
```

## Architecture

### Backend Pipeline

Data flows through a chain of single-responsibility modules in `backend/core/`:

```
ScanOrchestrator (orchestrator.py)
  ├── RestApiClient (api_client.py)        — Polygon.io HTTP client, 5 concurrent, exponential backoff, cache
  ├── UniverseBuilder (universe_builder.py) — Validates ticker list, deduplicates, uppercases
  ├── MarketRegimeAnalyzer (regime_analyzer.py) — Classifies market as bullish/bearish/neutral using SPY data
  ├── IndicatorCalculator (indicator_calculator.py) — Computes 10 indicators: SMA50, EMA20, EMA9, MACD, RSI14, ROC10, avg_volume_20, relative_strength, proximity_to_20d_high
  ├── ScoringEngine (scoring_engine.py)     — Gradient scoring 0–100; see scoring breakdown below
  │     ├── StageClassifier (stage_classifier.py) — Minervini Stage 2 classification (5 checks)
  │     └── PatternDetector (pattern_detector.py) — VCP, Flat Base, Darvas Box, Tight Flag
  └── RankingService (ranking_service.py)   — Sorts scored tickers by bullish_score desc
```

`ScanStore (scan_store.py)` persists completed scans to SQLite (`scanner.db`, path from `config.DB_PATH`).

**Backtesting** (`backend/backtest/`): `BacktestEngine` re-runs the scanner on historical dates via `as_of_date` parameter (point-in-time, no look-ahead). `metrics.py` computes confusion matrix, precision, recall, F1. Endpoints: `POST /api/v1/backtest/single` and `/api/v1/backtest/rolling`.

**Entry point**: `backend/main.py` — FastAPI app with CORS, two routers (`/api/v1` from `api/endpoints.py` and `api/backtest_endpoints.py`), and startup hook that initializes `ScanStore`.

**Config**: `backend/config.py` — reads env vars. `POLYGON_TOKEN` is required. No `.env` file needed if token is in shell profile.

### Scoring Engine (V2 Gradient)

`ScoringEngine.calculate_score()` produces 0–100 via five weighted components:

| Component | Max pts | Key signals |
|---|---|---|
| Trend Position | 20 | SMA50 + EMA20 proximity (gradient, not binary) |
| Recovery Bonus | 25 | Catches oversold bounces below SMA50 — main FN reducer |
| Extension Penalty | -15 | Penalizes stocks >15% above SMA50 or RSI>75 — main FP reducer |
| Momentum | 20 | MACD diff (normalized) + ROC10 |
| Strength | 20 | RSI14 (favors 50–70 zone) + Relative Strength vs SPY |
| Confirmation | 20 | Volume ratio + proximity to 20-day high |

`calculate_enhanced_score()` adds up to 20 bonus points for Stage 2 classification (10 pts) and pattern detection (10 pts).

**Optimal backtest settings** (from empirical tuning): Score ≥ 50, Gain ≥ 5%, Horizon = 30 days → Precision=66%, Recall=58%, F1=62% on 150 trades.

### Frontend

Single-page React app in `frontend/src/`:

- `App.tsx` — top-level state management; orchestrates scan and backtest flows
- `components/` — Cloudscape Design System components: `BacktestPanel`, `ResultsTable`, `ScanButton`, `MarketRegimeBadge`, `SignalBadges`, `LoadingIndicator`, `ErrorMessage`
- `services/scanApi.ts` + `services/backtestApi.ts` — typed fetch wrappers against backend
- `types/scan.ts` + `types/backtest.ts` — shared TypeScript types

UI is configured via `frontend/.env`: `VITE_API_URL=http://localhost:8000` (default).

### Tests

```
backend/tests/
  unit/       — per-module unit tests (mocked dependencies)
  property/   — hypothesis property-based tests (indicators, scoring, ranking, regime)
  integration/ — end-to-end tests hitting the FastAPI app via TestClient
  backtest/   — metrics computation tests
```

All tests run with `asyncio_mode = auto` (pytest-asyncio). Markers: `unit`, `property`, `integration`, `slow`.

### Ticker Lists

- `ALL_HALAL_STOCKS.txt` — 150+ halal-screened tickers (one per line)
- `halal_tickers_for_scanner.txt` — smaller curated list
- Frontend `BacktestPanel.tsx` has hardcoded presets (Top 20, Top 50, sector buckets) for quick selection

## Key Design Decisions

- **Gradient scoring (not binary)**: Each indicator contributes partial points based on proximity/strength. A stock at 1% above SMA50 scores 6 pts; 5%+ scores 10 pts. This prevents cliff-edge score jumps.
- **Recovery bonus**: Explicitly rewards stocks below SMA50 showing RSI recovery + positive ROC. This was added to reduce false negatives (missed winners in healthy pullbacks).
- **Extension penalty**: Stocks extended >15% above SMA50 with RSI>75 are penalized. Addresses false positives (stocks hitting all binary checks but actually overbought).
- **Point-in-time backtesting**: `as_of_date` parameter filters all API calls to data available on that date, preventing look-ahead bias.
- **No `.env` required for backend**: `POLYGON_TOKEN` must be a global shell env var (not loaded from file) — the app will raise on startup if missing.
