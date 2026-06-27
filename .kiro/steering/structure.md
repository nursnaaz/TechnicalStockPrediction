# Project Structure

## Current Organization

The project is organized as a full-stack application with separate backend and frontend:

```
TechnicalStockPrediction/
├── .git/                     # Git version control
├── .kiro/                    # Kiro AI assistant configuration
│   ├── specs/                # Feature specifications
│   │   └── bullish-stock-scanner/
│   │       ├── .config.kiro
│   │       ├── requirements.md
│   │       ├── design.md
│   │       └── tasks.md (future)
│   └── steering/             # AI guidance documents
├── backend/                  # Python FastAPI backend
├── frontend/                 # React TypeScript frontend
├── .gitignore                # Python and Node gitignore
├── LICENSE                   # Apache License 2.0
└── README.md                 # Project documentation
```

## Backend Structure

The backend follows a layered architecture with clear separation of concerns:

```
backend/
├── main.py                          # FastAPI application entry point
├── config.py                        # Configuration and environment variables
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables (gitignored)
├── api/                             # API layer
│   ├── __init__.py
│   ├── endpoints.py                 # API route handlers
│   └── models.py                    # Pydantic request/response models
├── core/                            # Business logic layer
│   ├── __init__.py
│   ├── api_client.py                # REST API Client (external data fetching)
│   ├── universe_builder.py          # Universe Builder (ticker validation)
│   ├── regime_analyzer.py           # Market Regime Analyzer
│   ├── indicator_calculator.py      # Technical Indicator Calculator
│   ├── scoring_engine.py            # Scoring Engine (bullish score calculation)
│   ├── ranking_service.py           # Ranking Service (ticker sorting)
│   ├── scan_store.py                # SQLite persistence for scan results
│   └── orchestrator.py              # Scan Orchestrator (pipeline coordination)
├── utils/                           # Utility layer
│   ├── __init__.py
│   └── logging.py                   # Logging configuration
└── tests/                           # Test suite
    ├── __init__.py
    ├── unit/                        # Unit tests for individual components
    │   ├── test_api_client.py
    │   ├── test_universe_builder.py
    │   ├── test_regime_analyzer.py
    │   ├── test_indicator_calculator.py
    │   ├── test_scoring_engine.py
    │   └── test_ranking_service.py
    ├── property/                    # Property-based tests (hypothesis)
    │   ├── test_indicators_properties.py
    │   ├── test_scoring_properties.py
    │   ├── test_ranking_properties.py
    │   └── test_api_client_properties.py
    └── integration/                 # Integration tests
        └── test_scan_endpoint.py
```

## Frontend Structure

The frontend follows a component-based architecture:

```
frontend/
├── package.json                     # Node dependencies and scripts (✓ initialized)
├── vite.config.ts                   # Vite build configuration (✓ initialized)
├── tsconfig.json                    # TypeScript configuration (✓ initialized)
├── tsconfig.app.json                # App TypeScript configuration (✓ initialized)
├── tsconfig.node.json               # Node TypeScript configuration (✓ initialized)
├── eslint.config.js                 # ESLint configuration (✓ initialized)
├── index.html                       # HTML entry point (✓ initialized)
├── .env                             # Environment variables (✓ created, gitignored)
├── src/
│   ├── App.tsx                      # Main application component (✓ implemented with full state management)
│   ├── main.tsx                     # React entry point (✓ initialized)
│   ├── components/                  # React components (✓ directory created)
│   │   ├── ScanButton.tsx           # Scan trigger button (✓ implemented)
│   │   ├── LoadingIndicator.tsx     # Loading state UI (✓ implemented)
│   │   ├── MarketRegimeBadge.tsx    # Market regime display (✓ implemented)
│   │   ├── ResultsTable.tsx         # Ranked ticker table (✓ implemented)
│   │   ├── SignalBadges.tsx         # Indicator signal badges (✓ implemented)
│   │   └── ErrorMessage.tsx         # Error display (✓ implemented)
│   ├── services/                    # Business logic services (✓ directory created)
│   │   └── scanApi.ts               # Backend API client (✓ implemented)
│   ├── types/                       # TypeScript type definitions (✓ directory created)
│   │   └── scan.ts                  # Scan-related types (✓ implemented)
│   └── styles/                      # CSS styles (✓ directory created)
│       └── App.css                  # Application styles (optional)
├── tests/                           # Test directory (✓ created)
│   ├── App.test.tsx                 # Component tests (✓ implemented)
│   └── e2e/                         # End-to-end tests (Playwright, ✓ implemented)
│       ├── happy-path.spec.ts       # Complete user workflow tests (✓ implemented)
│       ├── error-scenarios.spec.ts  # Error handling tests (✓ implemented)
│       ├── loading-states.spec.ts   # Loading state tests (✓ implemented)
│       ├── results-display.spec.ts  # Results rendering tests (✓ implemented)
│       └── comprehensive-test.spec.ts # Comprehensive E2E suite with 60+ screenshots (✓ implemented)
├── playwright.config.ts             # Playwright configuration (✓ created)
└── test-results/                    # Test results directory (✓ auto-generated)
    └── screenshots/                 # E2E test screenshots (✓ auto-generated)
```

## Naming Conventions

### Backend (Python)
- **Packages/Modules**: lowercase with underscores (`indicator_calculator`, `api_client`)
- **Classes**: PascalCase (`IndicatorCalculator`, `ScoringEngine`, `MarketRegime`)
- **Functions/Variables**: lowercase with underscores (`calculate_sma`, `bullish_score`)
- **Constants**: uppercase with underscores (`MAX_CONCURRENT_REQUESTS`, `DEFAULT_TICKERS`)
- **Async Functions**: prefix with `async` keyword, name like regular functions

### Frontend (TypeScript/React)
- **Components**: PascalCase (`ResultsTable`, `ScanButton`)
- **Component Files**: PascalCase matching component name (`ResultsTable.tsx`)
- **Functions/Variables**: camelCase (`handleScan`, `tickerScore`)
- **Types/Interfaces**: PascalCase (`ScanResponse`, `TickerScore`)
- **Constants**: UPPER_SNAKE_CASE or camelCase based on scope

## Layered Architecture

### Backend Layers

1. **API Layer** (`api/`): HTTP interface, request/response handling
   - Minimal business logic
   - Input validation with Pydantic
   - Error handling and HTTP status codes

2. **Core Layer** (`core/`): Business logic and domain models
   - Independent of API framework
   - Contains all calculation and processing logic
   - No HTTP or presentation concerns

3. **Utility Layer** (`utils/`): Shared utilities and cross-cutting concerns
   - Logging configuration
   - Common helpers
   - No business logic

### Frontend Layers

1. **Component Layer** (`components/`): UI components
   - Presentation logic only
   - Receives data via props
   - Emits events via callbacks

2. **Service Layer** (`services/`): Business logic and API communication
   - API client functions
   - Data transformation
   - Error handling

3. **Type Layer** (`types/`): TypeScript type definitions
   - Interface definitions
   - Type aliases
   - Enums

## Component Responsibilities

### Backend Components

- **API Client**: External API communication, retry logic, caching
- **Universe Builder**: Ticker validation and universe construction
- **Market Regime Analyzer**: Market condition classification
- **Indicator Calculator**: Technical indicator computation
- **Scoring Engine**: Bullish score calculation based on signals
- **Ranking Service**: Ticker sorting and ranking
- **Orchestrator**: Pipeline coordination and error handling

### Frontend Components

- **App**: Main container, state management, orchestration
- **ScanButton**: User interaction trigger
- **LoadingIndicator**: Async operation feedback
- **MarketRegimeBadge**: Market condition display
- **ResultsTable**: Tabular data presentation
- **SignalBadges**: Visual indicator signal representation
- **ErrorMessage**: Error feedback display

## File Organization Principles

1. **Separation of Concerns**: API, business logic, and utilities are separated
2. **Single Responsibility**: Each module has one clear purpose
3. **Dependency Direction**: API layer depends on core, core is independent
4. **Testability**: Core logic is easily testable without API infrastructure
5. **Modularity**: Components can be developed and tested independently

## Configuration Management

### Backend Configuration
- Environment variables in `.env` file (gitignored)
- Configuration loading in `config.py`
- Type-safe settings with Pydantic

### Frontend Configuration
- Environment variables in `.env` file (gitignored)
- Vite-specific prefix: `VITE_`
- Import via `import.meta.env`

## Testing Organization

### Backend Tests
- **Unit Tests**: Test individual functions and classes in isolation
- **Property Tests**: Test mathematical properties across random inputs
- **Integration Tests**: Test API endpoints and full pipeline

### Frontend Tests
- **Component Tests**: Test UI components with React Testing Library
- **Integration Tests**: Test user interactions and API communication
- **E2E Tests**: Test complete user workflows with Playwright (browser automation)
