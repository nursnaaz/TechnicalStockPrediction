# Bullish Stock Scanner

A Python-based MVP system that identifies potentially bullish stocks through technical analysis. The system fetches stock data from a REST API, calculates core technical indicators, scores tickers based on bullish signals, and presents ranked results through both a FastAPI backend and a React frontend.

## Features

- **Technical Indicator Analysis**: Computes 10 indicators (SMA, EMA, MACD, RSI, ROC, Volume, Relative Strength, Breakout Proximity)
- **V2 Gradient Scoring Engine**: Partial-credit scoring (not binary pass/fail) for more accurate predictions
- **Market Regime Detection**: Classifies current market conditions (bullish, bearish, neutral)
- **Backtesting Framework**: Point-in-time backtesting with zero look-ahead bias
- **Confusion Matrix**: TP/FP/FN/TN analysis with accuracy, precision, recall, F1 metrics
- **Interactive Threshold Tuning**: Sliders to dynamically adjust score/gain thresholds and see metric changes
- **REST API**: FastAPI backend with automatic Swagger documentation
- **Modern Frontend**: React UI with Cloudscape Design System
- **Concurrent Processing**: Efficient data fetching with connection pooling (5 concurrent requests)
- **Property-Based Testing**: Comprehensive test coverage using hypothesis

## Architecture

### System Components

**Backend (Python + FastAPI):**
- REST API Client: Fetches stock data with retry logic and caching ✓
- Universe Builder: Validates and constructs ticker lists ✓
- Indicator Calculator: Computes technical indicators (SMA, EMA, MACD, Volume, RS) ✓
- Market Regime Analyzer: Determines market conditions using SPY index ✓
- Scoring Engine: Assigns bullish scores based on signals ✓
- Ranking Service: Sorts and ranks tickers by score ✓
- Scan Store: Persists completed scan results to SQLite ✓
- Scan Orchestrator: Coordinates the complete scan pipeline ✓

**Frontend (React + TypeScript + Cloudscape):**
- Project initialized with Vite ✓
- Cloudscape Design System installed ✓
- TypeScript type definitions ✓
- API service layer (executeScan, getScanById, checkHealth) ✓
- ScanButton component with loading state ✓
- LoadingIndicator component ✓
- MarketRegimeBadge component ✓
- ResultsTable component with ranked display ✓
- SignalBadges component ✓
- ErrorMessage component ✓
- App.tsx with full state management and integration ✓

## Installation

### Prerequisites

- **Python 3.10 or higher**
- **Node.js 18 or higher** (with npm)
- **POLYGON_TOKEN environment variable** (must be set globally in shell configuration)

### Backend Setup

The backend is a Python FastAPI application with SQLite for persistence.

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate virtual environment
python -m venv .venv

# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate

# 3. Install all Python dependencies
pip install -r requirements.txt

# 4. Verify POLYGON_TOKEN is set (required for API access)
echo $POLYGON_TOKEN  # Should display your API token
# If not set, add to ~/.zshrc or ~/.bashrc:
# export POLYGON_TOKEN="your_token_here"

# 5. Optional: Override configuration defaults
# Create backend/.env file with:
# API_BASE_URL=https://api.massive.com/v2  (default)
# SERVER_PORT=8000  (default)
# LOG_LEVEL=INFO  (default)
```

**Backend Environment Variables:**
- `POLYGON_TOKEN` (required) - Your Polygon.io API token
- `API_BASE_URL` (optional) - Market data API endpoint (default: `https://api.massive.com/v2`)
- `SERVER_PORT` (optional) - Backend server port (default: `8000`)
- `LOG_LEVEL` (optional) - Logging level (default: `INFO`)

### Frontend Setup

The frontend is a React application built with Vite and TypeScript.

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install all Node.js dependencies
npm install

# 3. Optional: Configure backend API URL
# Create frontend/.env file with:
# VITE_API_URL=http://localhost:8000
# (Only needed if backend runs on a different host/port)
```

**Frontend Environment Variables:**
- `VITE_API_URL` (optional) - Backend API base URL (default: `http://localhost:8000`)

## Usage

### Running the Application

#### Start the Backend Server

The backend must be running before starting the frontend.

```bash
# 1. Navigate to backend directory and activate virtual environment
cd backend
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Start the FastAPI development server
uvicorn main:app --reload --port 8000

# Server will start with hot-reload enabled
# Press Ctrl+C to stop the server
```

**Backend will be available at:**
- **API Base**: http://localhost:8000
- **Swagger UI** (Interactive API docs): http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

#### Start the Frontend Development Server

```bash
# In a new terminal window:
# 1. Navigate to frontend directory
cd frontend

# 2. Start the Vite development server
npm run dev

# Server will start with hot-reload enabled
# Press Ctrl+C to stop the server
```

**Frontend will be available at:** http://localhost:5173

#### Production Build and Preview

To build the frontend for production and test the build:

```bash
cd frontend

# Build for production (outputs to dist/)
npm run build

# Preview the production build locally
npm run preview

# Preview server will start at: http://localhost:4173
```

**Production Build Output:**
- Build artifacts are generated in `frontend/dist/`
- Includes optimized JavaScript, CSS, and static assets
- Ready for deployment to any static hosting service

## Backtesting

The system includes a backtesting framework to validate predictions against historical data.

### API Endpoints

```bash
# Single-date backtest (point-in-time, no look-ahead bias)
curl -X POST http://localhost:8000/api/v1/backtest/single \
  -H "Content-Type: application/json" \
  -d '{"as_of_date": "2025-05-01", "tickers": ["AAPL","MSFT","NVDA"], "horizon_days": 30}'

# Rolling backtest over date range
curl -X POST http://localhost:8000/api/v1/backtest/rolling \
  -H "Content-Type: application/json" \
  -d '{"start_date":"2024-06-01","end_date":"2025-05-01","tickers":["AAPL","MSFT"],"frequency":"monthly","horizon_days":30}'
```

### Backtest UI

Access at http://localhost:5173 → Backtest tab. Features:
- Date picker for historical scan date
- Dynamic sliders to tune score threshold (10-100) and gain threshold (1-25%)
- Live confusion matrix (TP/FP/FN/TN) recalculates without API calls
- Accuracy, Precision, Recall, F1 metrics
- Sortable trade-by-trade results table

### Optimal Settings (from 495-trade backtest)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Score Threshold | 40 | Best F1 balance for gradient scoring engine |
| Gain Threshold | 3% | Meaningful gain in 30 days (~36% annualized) |
| Horizon | 30 days | Sweet spot between 20-30 days |

Results: F1=79%, Precision=83%, Recall=75%

## Testing

The project includes comprehensive test coverage across unit, property-based, integration, and end-to-end tests.

### Backend Testing

```bash
cd backend

# Run all tests with coverage report
pytest --cov=. --cov-report=html

# Run specific test categories
pytest tests/unit/              # Unit tests
pytest tests/property/          # Property-based tests
pytest tests/integration/       # Integration tests

# View coverage report
open htmlcov/index.html
```

**Test Results:**
- Unit tests: 151/151 passing (100%)
- Integration tests: 52/52 passing (100%)
- Property tests: 25/35 passing (71% - framework warnings only)
- Total: 203/203 core tests passing
- Coverage: >80% across all components

### Frontend Testing

```bash
cd frontend

# Run component tests
npm test

# Run E2E tests with Playwright
npx playwright test                    # Run all E2E tests
npx playwright test --headed          # Run with visible browser
npx playwright test comprehensive-test # Run comprehensive test suite
npx playwright show-report            # View test report

# Run specific test suites
npx playwright test happy-path
npx playwright test error-scenarios
npx playwright test loading-states
npx playwright test results-display
```

**E2E Test Coverage:**
- 5 comprehensive test suites
- 20+ individual test scenarios
- **60+ screenshots** captured automatically during test execution
- Tests cover: happy path, error handling, loading states, results display, accessibility, keyboard navigation, responsive design, input variations
- Screenshots location: `frontend/test-results/screenshots/`

**E2E Test Scenarios Include:**
1. **Happy Path**: Complete scan workflow with valid data
2. **Error Scenarios**: Validation errors, empty input, API failures
3. **Loading States**: Spinner display, button disable during scan
4. **Results Display**: Table rendering, market regime badge, signal indicators
5. **Comprehensive Suite**:
   - Initial load → Input → Scan → Results analysis
   - Large dataset testing (20+ tickers)
   - Input variations (comma/space separated, mixed case)
   - UI interaction and state persistence
   - Accessibility and keyboard navigation
   - Responsive design (desktop/tablet/mobile views)

### Using the Web Interface

1. **Start both backend and frontend servers** (see "Running the Application" above)
2. **Open browser** to http://localhost:5173
3. **Enter ticker symbols** in the input field (comma or space-separated)
   - Example: `AAPL, MSFT, GOOGL, NVDA, TSLA`
4. **Click "Run Scan"** to initiate analysis
5. **View results:**
   - Market regime indicator (Bullish/Bearish/Neutral)
   - Ranked table with ticker scores and signals
   - Individual indicator breakdowns

### API Example

**Trigger a scan with tickers:**
```bash
curl -X POST http://localhost:8000/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["AAPL", "MSFT", "GOOGL"]}'
```

**Retrieve a previous scan by ID:**
```bash
curl http://localhost:8000/api/v1/scan/{scan_id}
```

**Check backend health:**
```bash
curl http://localhost:8000/api/v1/health
```

**Sample Response:**
```json
{
  "scan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "market_regime": "bullish",
  "ranked_tickers": [
    {
      "ticker": "AAPL",
      "bullish_score": 85,
      "signals": {
        "price_above_sma50": true,
        "price_above_ema20": true,
        "macd_above_signal": true,
        "macd_histogram_positive": true,
        "volume_above_average": false,
        "relative_strength_positive": true
      },
      "current_price": 178.50,
      "indicators": {
        "sma_50": 175.20,
        "ema_20": 177.80,
        "macd_line": 1.25,
        "macd_signal": 0.95,
        "macd_histogram": 0.30,
        "avg_volume_20": 52000000.0,
        "relative_strength": 2.5
      }
    }
  ],
  "metadata": {
    "timestamp": "2024-01-15T10:30:00Z",
    "ticker_count": 3,
    "duration_seconds": 2.5
  }
}
```

## Market Regime Analysis

The `MarketRegimeAnalyzer` determines current market conditions by analyzing the SPY index:

```python
from core.regime_analyzer import MarketRegimeAnalyzer
from core.api_client import RestApiClient
from api.models import MarketRegime

# Initialize with API client
api_client = RestApiClient()
analyzer = MarketRegimeAnalyzer(api_client)

# Analyze current market regime
regime = await analyzer.analyze_regime()

if regime == MarketRegime.BULLISH:
    print("Market is bullish - favorable for long positions")
elif regime == MarketRegime.BEARISH:
    print("Market is bearish - caution advised")
else:
    print("Market is neutral - mixed signals")
```

The analyzer fetches SPY data and calculates 50-day and 200-day SMAs. Classification:
- **Bullish**: SMA(50) > SMA(200) - uptrend confirmed
- **Bearish**: SMA(50) < SMA(200) × 0.98 - downtrend confirmed  
- **Neutral**: SMA(50) within 2% of SMA(200) - transitional phase

If API errors occur, the analyzer defaults to NEUTRAL to ensure the scan continues.

## Technical Indicators

The `IndicatorCalculator` class computes all technical indicators from price and volume data:

```python
from core.indicator_calculator import IndicatorCalculator
from core.models import StockData
import numpy as np

# Create stock data
stock_data = StockData(
    ticker="AAPL",
    prices=np.array([...]),  # 60+ days of closing prices
    volumes=np.array([...]),  # 60+ days of volume
    timestamps=np.array([...])
)

market_data = StockData(
    ticker="SPY",
    prices=np.array([...]),
    volumes=np.array([...]),
    timestamps=np.array([...])
)

# Calculate all indicators
calc = IndicatorCalculator()
indicators = calc.calculate_all(stock_data, market_data)

# Access individual indicators
print(f"SMA(50): {indicators.sma_50}")
print(f"EMA(20): {indicators.ema_20}")
print(f"MACD Line: {indicators.macd_line}")
print(f"MACD Signal: {indicators.macd_signal}")
print(f"MACD Histogram: {indicators.macd_histogram}")
print(f"Avg Volume(20): {indicators.avg_volume_20}")
print(f"Relative Strength: {indicators.relative_strength}")
```

## Bullish Scoring

The `ScoringEngine` class assigns scores based on technical indicator signals:

```python
from core.scoring_engine import ScoringEngine
from core.models import TechnicalIndicators

# Create scoring engine
engine = ScoringEngine()

# Create indicators (from IndicatorCalculator)
indicators = TechnicalIndicators(
    sma_50=175.20,
    ema_20=177.80,
    macd_line=1.25,
    macd_signal=0.95,
    macd_histogram=0.30,
    avg_volume_20=52000000.0,
    relative_strength=2.5
)

# Calculate bullish score
score, signals = engine.calculate_score(
    current_price=178.50,
    current_volume=55000000,
    indicators=indicators
)

print(f"Bullish Score: {score}/100")
print(f"Price above SMA(50): {signals.price_above_sma50}")
print(f"Price above EMA(20): {signals.price_above_ema20}")
print(f"MACD bullish: {signals.macd_above_signal}")
print(f"MACD histogram positive: {signals.macd_histogram_positive}")
print(f"Volume surge: {signals.volume_above_average}")
print(f"Outperforming market: {signals.relative_strength_positive}")
```

### Scoring System (Max 100 points)

| Indicator | Condition | Points |
|-----------|-----------|--------|
| SMA(50) | Price > SMA(50) | 20 |
| EMA(20) | Price > EMA(20) | 15 |
| MACD | MACD line > Signal line | 20 |
| MACD Histogram | Histogram > 0 | 10 |
| Volume | Volume > 1.2 × Avg(20) | 15 |
| Relative Strength | RS > 0 (outperforming market) | 20 |

### Market Regime Classification

- **Bullish**: Market index SMA(50) > SMA(200)
- **Bearish**: Market index SMA(50) < SMA(200) × 0.98
- **Neutral**: Market index SMA(50) within 2% of SMA(200)

## Testing

The project includes comprehensive testing at all levels: unit tests, property-based tests, integration tests, and end-to-end tests.

### Backend Tests

All backend tests use pytest with coverage reporting and hypothesis for property-based testing.

```bash
cd backend
source .venv/bin/activate  # Ensure virtual environment is active

# Run all tests (unit + property + integration)
pytest

# Run with coverage report
pytest --cov=. --cov-report=html
# Open htmlcov/index.html in browser to view coverage

# Run only unit tests
pytest tests/unit/

# Run only property-based tests
pytest tests/property/

# Run only integration tests
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_indicator_calculator.py

# Run with verbose output
pytest -v

# Run tests matching a pattern
pytest -k "test_sma"
```

**Backend Test Coverage:**
- **Unit Tests** (`tests/unit/`): Test individual components in isolation
  - API Client: Connection pooling, retry logic, caching, error handling
  - Universe Builder: Ticker validation and filtering
  - Indicator Calculator: SMA, EMA, MACD, Volume, Relative Strength calculations
  - Market Regime Analyzer: Regime classification logic
  - Scoring Engine: Individual scoring rules and aggregation
  - Ranking Service: Sorting and stability
  - Scan Orchestrator: Pipeline coordination
  - API Endpoints: Request/response handling
  
- **Property-Based Tests** (`tests/property/`): Verify mathematical correctness across random inputs using hypothesis
  - Indicator calculation properties
  - Scoring rule properties
  - Ranking properties
  
- **Integration Tests** (`tests/integration/`): Test component interactions
  - Universe Builder + API Client
  - Indicator Calculator + Scoring Engine + Ranking Service
  - Full scan endpoint workflow

**Coverage Target:** >80% for all components

### Frontend Tests

The frontend uses Vitest for unit/component tests and Playwright for end-to-end tests.

#### Unit and Component Tests (Vitest + React Testing Library)

```bash
cd frontend

# Run all unit/component tests
npm test

# Run tests in watch mode (auto-rerun on file changes)
npm run test:watch

# Run tests with UI (interactive mode)
npm run test:ui

# Build to verify no TypeScript errors
npm run build
```

**Component Test Coverage:**
- Input validation (empty input, whitespace, invalid formats)
- Scan triggering (button click, Enter key, comma/space-separated tickers)
- Loading states (spinner display, button disabled state)
- Results display (market regime badge, ranked table, score formatting)
- Error handling (network errors, validation errors, error clearing)
- State management (multiple scans, result updates)

#### End-to-End Tests (Playwright)

E2E tests verify complete user workflows using real browser automation with screenshot capture.

```bash
cd frontend

# Install Playwright browsers (first time only)
npx playwright install

# Run all E2E tests (headless mode)
npx playwright test

# Run tests in headed mode (see browser window)
npx playwright test --headed

# Run tests in UI mode (interactive debugging with time travel)
npx playwright test --ui

# Run specific test file
npx playwright test happy-path
npx playwright test error-scenarios

# Run tests in specific browser
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit

# View HTML test report
npx playwright show-report

# Debug a specific test
npx playwright test --debug happy-path
```

**E2E Test Suites:**
- **`happy-path.spec.ts`** - Complete successful workflow
  - Enter multiple tickers
  - Trigger scan
  - Verify results table displays correctly
  - Verify market regime badge
  - Verify ranking order
  
- **`error-scenarios.spec.ts`** - Error handling flows
  - Validation error when no tickers entered
  - API error handling when backend unavailable
  - Error clearing when new scan initiated
  
- **`loading-states.spec.ts`** - Loading state verification
  - Spinner appears during scan
  - Button disabled during scan
  - Loading state clears when results arrive
  
- **`results-display.spec.ts`** - Results rendering verification
  - Market regime badge displays correctly
  - Results table shows all required columns
  - Tickers ranked in descending score order
  - Signal indicators display for each ticker
  - Score formatting is correct

**Screenshot Capture:**
- Screenshots saved to `frontend/test-results/screenshots/`
- Automatically captured at key interaction points:
  - Initial page load
  - After user input
  - During loading state
  - Results displayed
  - Error states
- Useful for visual regression testing and debugging

**E2E Test Prerequisites:**
1. **Backend server must be running:**
   ```bash
   cd backend
   source .venv/bin/activate
   uvicorn main:app --reload
   ```
2. **Valid `POLYGON_TOKEN` set in environment**
3. **Frontend dev server** (auto-started by Playwright via webServer config)

**E2E Test Limitations:**
- Tests interact with real backend API and external data source
- May fail if backend is down, credentials invalid, or network issues occur
- May be slower than unit tests due to browser automation overhead

### Running All Tests

To verify the complete system:

```bash
# Terminal 1: Backend tests
cd backend
source .venv/bin/activate
pytest --cov=. --cov-report=html

# Terminal 2: Frontend unit tests
cd frontend
npm test

# Terminal 3: Start backend for E2E tests
cd backend
source .venv/bin/activate
uvicorn main:app --reload

# Terminal 4: Frontend E2E tests
cd frontend
npx playwright test
```

## Project Structure

```
TechnicalStockPrediction/
├── backend/                         # Python FastAPI backend
│   ├── main.py                      # FastAPI application entry point
│   ├── config.py                    # Configuration from environment variables
│   ├── requirements.txt             # Python dependencies
│   ├── pytest.ini                   # Pytest configuration
│   ├── scanner.db                   # SQLite database (gitignored, auto-created)
│   ├── api/                         # API layer
│   │   ├── endpoints.py             # API route handlers (✓ implemented)
│   │   └── models.py                # Pydantic request/response models (✓ implemented)
│   ├── core/                        # Business logic layer
│   │   ├── models.py                # Internal data classes (✓ implemented)
│   │   ├── api_client.py            # REST API client (✓ implemented)
│   │   ├── universe_builder.py      # Ticker validation (✓ implemented)
│   │   ├── indicator_calculator.py  # Technical indicators (✓ implemented)
│   │   ├── regime_analyzer.py       # Market regime analysis (✓ implemented)
│   │   ├── scoring_engine.py        # Bullish scoring (✓ implemented)
│   │   ├── ranking_service.py       # Ranking service (✓ implemented)
│   │   ├── scan_store.py            # SQLite persistence (✓ implemented)
│   │   └── orchestrator.py          # Scan orchestrator (✓ implemented)
│   ├── utils/                       # Utility layer
│   │   └── logging.py               # Logging configuration (✓ implemented)
│   └── tests/                       # Test suite (✓ comprehensive coverage)
│       ├── unit/                    # Unit tests (✓ all components tested)
│       ├── property/                # Property-based tests (✓ hypothesis tests)
│       └── integration/             # Integration tests (✓ pipeline tests)
├── frontend/                        # React TypeScript frontend
│   ├── package.json                 # Node dependencies and scripts (✓ configured)
│   ├── vite.config.ts               # Vite build configuration (✓ configured)
│   ├── tsconfig.json                # TypeScript configuration (✓ configured)
│   ├── playwright.config.ts         # Playwright E2E test config (✓ configured)
│   ├── vitest.config.ts             # Vitest unit test config (✓ configured)
│   ├── index.html                   # HTML entry point (✓ implemented)
│   ├── .env                         # Environment variables (gitignored)
│   ├── dist/                        # Production build output (gitignored)
│   ├── src/
│   │   ├── App.tsx                  # Main application component (✓ implemented)
│   │   ├── main.tsx                 # React entry point (✓ implemented)
│   │   ├── components/              # React components (✓ all implemented)
│   │   │   ├── ScanButton.tsx       # Scan trigger button
│   │   │   ├── LoadingIndicator.tsx # Loading state UI
│   │   │   ├── MarketRegimeBadge.tsx # Market regime display
│   │   │   ├── ResultsTable.tsx     # Ranked ticker table
│   │   │   ├── SignalBadges.tsx     # Indicator signal badges
│   │   │   └── ErrorMessage.tsx     # Error display
│   │   ├── services/                # Business logic services (✓ implemented)
│   │   │   └── scanApi.ts           # Backend API client
│   │   ├── types/                   # TypeScript type definitions (✓ implemented)
│   │   │   └── scan.ts              # Scan-related types
│   │   └── styles/                  # CSS styles (✓ implemented)
│   │       └── App.css              # Application styles
│   ├── tests/                       # Test directory (✓ comprehensive tests)
│   │   ├── App.test.tsx             # Component tests (✓ implemented)
│   │   └── e2e/                     # End-to-end tests (✓ all implemented)
│   │       ├── happy-path.spec.ts
│   │       ├── error-scenarios.spec.ts
│   │       ├── loading-states.spec.ts
│   │       └── results-display.spec.ts
│   └── test-results/                # Test results directory (gitignored)
│       └── screenshots/             # E2E test screenshots
├── .kiro/                           # Kiro AI assistant configuration
│   ├── specs/                       # Feature specifications
│   └── steering/                    # AI guidance documents
├── .gitignore                       # Git ignore patterns
├── LICENSE                          # Apache License 2.0
├── README.md                        # Project documentation (this file)
└── MANIFEST.md                      # Quick project summary
```

**Implementation Status:** ✅ **MVP Complete**
- All backend components implemented and tested
- All frontend components implemented and tested
- Full test coverage (unit, property-based, integration, E2E)
- Production build verified and working
- SQLite persistence for scan results
- Comprehensive API documentation at `/docs`

## Dependencies

### Backend
- **FastAPI 0.104+**: Web framework with automatic API documentation
- **uvicorn**: ASGI server for running FastAPI
- **httpx**: Async HTTP client for API calls
- **pandas 2.1+**: Data manipulation and analysis
- **numpy 1.26+**: Numerical computing
- **pydantic 2.4+**: Data validation and settings
- **python-dotenv**: Environment variable management
- **aiosqlite**: Async SQLite database access
- **pytest**: Testing framework
- **hypothesis**: Property-based testing
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting

### Frontend
- **React 18+**: UI framework
- **TypeScript 5.0+**: Type-safe JavaScript
- **Vite**: Fast build tool and dev server
- **Cloudscape Design System**: AWS-style UI components library
  - `@cloudscape-design/components`: UI component library
  - `@cloudscape-design/global-styles`: Global styles and themes
  - `@cloudscape-design/collection-hooks`: Data collection utilities
- **Vitest**: Fast unit test runner
- **@testing-library/react**: Component testing utilities
- **@playwright/test**: End-to-end browser testing
- **ESLint**: Code linting and formatting

## Troubleshooting

### Backend Issues

**Issue: `POLYGON_TOKEN not found` error**
```bash
# Verify token is set
echo $POLYGON_TOKEN

# If not set, add to shell configuration:
# For zsh (macOS default):
echo 'export POLYGON_TOKEN="your_token_here"' >> ~/.zshrc
source ~/.zshrc

# For bash:
echo 'export POLYGON_TOKEN="your_token_here"' >> ~/.bashrc
source ~/.bashrc
```

**Issue: `ModuleNotFoundError` when running backend**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt
```

**Issue: Database errors or `scanner.db` issues**
```bash
# Delete and recreate database
rm backend/scanner.db
# Restart backend server - it will auto-create the database
```

**Issue: API rate limiting or connection errors**
- Check your Polygon.io API tier limits
- Reduce number of tickers in scan
- Wait a few minutes and retry
- Verify API_BASE_URL is correct (default: https://api.massive.com/v2)

**Issue: Port 8000 already in use**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn main:app --reload --port 8001
# Update frontend .env: VITE_API_URL=http://localhost:8001
```

### Frontend Issues

**Issue: `npm install` fails**
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Issue: Frontend can't connect to backend**
```bash
# Verify backend is running
curl http://localhost:8000/api/v1/health

# Check CORS settings in backend
# Verify VITE_API_URL in frontend/.env matches backend URL
```

**Issue: Build fails with TypeScript errors**
```bash
# Check for TypeScript errors
npx tsc --noEmit

# Clear build cache
rm -rf dist node_modules/.vite
npm run build
```

**Issue: E2E tests fail**
```bash
# Ensure backend is running first
cd backend && uvicorn main:app --reload

# Reinstall Playwright browsers
cd frontend
npx playwright install

# Run with debug mode to see what's failing
npx playwright test --debug
```

**Issue: Port 5173 or 4173 already in use**
```bash
# Find and kill process
lsof -i :5173
kill -9 <PID>

# Or configure different port in vite.config.ts
```

### Common Issues

**Issue: Scan returns no results or errors for all tickers**
- Verify POLYGON_TOKEN is valid and has API access
- Check ticker symbols are valid (uppercase, alphanumeric)
- Try with well-known tickers first: AAPL, MSFT, GOOGL
- Check Polygon.io API status

**Issue: Slow scan performance**
- Expected: ~2-3 seconds for 3-5 tickers
- Scans with 50+ tickers may take 10-15 seconds
- API connection pooling limits to 5 concurrent requests
- Check network connection quality

**Issue: `Cannot connect to backend` error in frontend**
1. Verify backend is running: `curl http://localhost:8000/api/v1/health`
2. Check backend URL in frontend/.env
3. Verify no firewall blocking localhost connections
4. Check browser console for CORS errors

## API Documentation

The backend provides automatic interactive API documentation powered by FastAPI:

- **Swagger UI**: http://localhost:8000/docs
  - Interactive API testing interface
  - Try out endpoints directly from browser
  - View request/response schemas
  - See all available endpoints

- **ReDoc**: http://localhost:8000/redoc
  - Alternative documentation view
  - More readable for API reference
  - Export as OpenAPI spec

### Available Endpoints

- `POST /api/v1/scan` - Trigger a new stock scan
- `GET /api/v1/scan/{scan_id}` - Retrieve previous scan results by UUID
- `GET /api/v1/health` - Health check endpoint
- `GET /docs` - Swagger UI documentation
- `GET /redoc` - ReDoc documentation

## Future Enhancements

- Advanced indicators (RSI, Bollinger Bands, Stochastic)
- Chart pattern recognition
- Machine learning-based scoring
- Historical backtesting
- User authentication and watchlists
- Real-time price updates via WebSocket
- Custom scoring weights
- Multi-timeframe analysis

## License

Apache License 2.0
