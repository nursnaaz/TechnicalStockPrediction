# Bullish Stock Scanner

Technical analysis tool that identifies bullish stocks using indicators and scoring.

## Folders

- **backend/** - Python FastAPI server with indicator calculations, scoring, and persistence
- **frontend/** - React TypeScript UI with Cloudscape Design System components
- **.kiro/** - Kiro AI configuration and feature specs

## Key Files

- **backend/main.py** - FastAPI app entry point with CORS and endpoints
- **backend/core/indicator_calculator.py** - Calculates SMA, EMA, MACD, volume, relative strength
- **backend/core/scoring_engine.py** - Assigns 0-100 bullish scores based on signals
- **backend/core/orchestrator.py** - Coordinates scan pipeline from input to ranked results
- **backend/core/scan_store.py** - SQLite persistence for completed scans
- **frontend/src/App.tsx** - Main React component with state management
- **frontend/src/services/scanApi.ts** - Backend API client
- **frontend/src/components/ResultsTable.tsx** - Ranked tickers table display
- **frontend/tests/App.test.tsx** - Component tests with React Testing Library
- **frontend/tests/e2e/** - Playwright E2E tests with screenshots
- **frontend/playwright.config.ts** - Playwright test configuration
- **halal_stocks_usa.md** - Reference list of 200+ Shariah-compliant US stocks with tickers
- **halal_tickers_for_scanner.txt** - Ready-to-paste ticker lists (15 preset options)
- **ALL_HALAL_STOCKS.txt** - Comprehensive comma-separated lists (150+ stocks, sector-specific)
- **V2_DEVELOPMENT_PLAN.md** - Roadmap for V2: Phoenix rules, backtesting framework, 4-week plan

## Status

Built:
- Backend API with 8 core components (client, universe builder, indicators, regime, scoring, ranking, store, orchestrator)
- Unit tests and property-based tests for all backend components (>80% coverage)
- Integration tests for scan endpoint
- Frontend with App component and 6 child components (ScanButton, LoadingIndicator, MarketRegimeBadge, ResultsTable, SignalBadges, ErrorMessage)
- Frontend component tests using Vitest and React Testing Library
- Playwright E2E tests with 4 test suites (happy-path, error-scenarios, loading-states, results-display)
- Screenshot capture at key interaction points for all E2E tests
- API service layer with executeScan, getScanById, checkHealth
- TypeScript type definitions for all API models
- SQLite persistence for scan results with UUID retrieval

Not built:
- Production deployment configuration

## Running

Backend:
```
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

Frontend:
```
cd frontend
npm run dev
```

Tests:
```
cd backend && pytest --cov=. --cov-report=html
cd frontend && npm test
cd frontend && npx playwright test
cd frontend && npx playwright test --headed
cd frontend && npx playwright show-report
```

Build:
```
cd frontend && npm run build
```

API docs: http://localhost:8000/docs
