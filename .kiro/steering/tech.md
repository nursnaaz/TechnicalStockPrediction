# Technology Stack

## Languages

### Backend
**Python 3.10+** - Primary backend development language

### Frontend
**TypeScript/JavaScript** - Frontend development with React

## Backend Stack

### Web Framework
- **FastAPI 0.104+**: Modern, fast web framework with automatic API documentation
- **Uvicorn**: ASGI server for running FastAPI applications

### HTTP & Networking
- **httpx**: Async HTTP client for external API calls
- **python-dotenv**: Environment variable management

### Data Processing
- **pandas 2.1+**: Data manipulation and time series analysis
- **numpy 1.26+**: Numerical computing for indicator calculations

### API & Validation
- **Pydantic 2.4+**: Data validation and settings management
- **FastAPI middleware**: CORS support for frontend integration

## Frontend Stack

### Framework & Build
- **React 18+**: UI framework
- **Vite**: Fast build tool and dev server
- **TypeScript 5.0+**: Type-safe JavaScript

### UI Library
- **Cloudscape Design System**: `@cloudscape-design/components` for UI elements

### HTTP Client
- **Fetch API**: Native browser API for HTTP requests

## Dependencies & Package Management

### Backend
The project uses pip with requirements.txt:
- Production dependencies in `requirements.txt`
- Development/testing dependencies included in the same file

### Frontend
The project uses npm with package.json:
- Runtime dependencies
- Dev dependencies for build and testing

## Environment Management

### Backend
Virtual environments for dependency isolation:
- `.venv/` or `venv/` directories are gitignored
- Environment variables stored in `.env` files (gitignored)

Required environment variables:
- `API_KEY`: External market data API key
- `API_SECRET`: External market data API secret
- `API_BASE_URL`: Market data API endpoint
- `SERVER_PORT`: Backend server port (default: 8000)

### Frontend
Environment variables in `.env` files:
- `VITE_API_URL`: Backend API URL (default: http://localhost:8000)

## Development Tools

### Backend Tools
- **Testing**: pytest, hypothesis (property-based testing), pytest-asyncio, pytest-cov
- **Linting**: ruff
- **Type Checking**: mypy
- **ASGI Server**: uvicorn with reload

### Frontend Tools
- **Testing**: vitest, @testing-library/react, @testing-library/jest-dom, @testing-library/user-event, @playwright/test (E2E testing)
- **Build**: Vite with React plugin
- **Type Checking**: TypeScript compiler

## Common Commands

### Backend Commands

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload --port 8000

# Run tests
pytest
pytest --cov=. --cov-report=html

# Run property-based tests
pytest tests/property/

# Run specific test file
pytest tests/unit/test_indicator_calculator.py

# Linting
ruff check .

# Type checking
mypy .
```

### Frontend Commands

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Run tests
npm test

# Run E2E tests with Playwright
npx playwright test

# Run E2E tests in UI mode
npx playwright test --ui

# Run E2E tests in headed mode (see browser)
npx playwright test --headed

# View E2E test report
npx playwright show-report

# Preview production build
npm run preview
```

## Code Quality

### Backend
- Type checking with mypy for type safety
- Ruff for fast linting and formatting
- Coverage reporting for tests (target: >80%)
- Property-based testing with hypothesis for mathematical correctness

### Frontend
- TypeScript for compile-time type safety
- React Testing Library for component testing
- ESLint integration via Vite

## API Documentation

- **Swagger UI**: Automatically generated at `/docs` endpoint
- Interactive API testing interface
- OpenAPI 3.0 specification

## Performance Considerations

### Backend
- Async/await for all I/O operations
- Connection pooling (max 5 concurrent API requests)
- In-memory caching per scan session
- Exponential backoff for retry logic

### Frontend
- Lazy loading for large result sets
- Debouncing for user interactions
- Optimistic UI updates
