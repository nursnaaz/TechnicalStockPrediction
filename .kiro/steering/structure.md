# Project Structure

## Current Organization

The project is in early stages with minimal structure:

```
TechnicalStockPrediction/
├── .git/               # Git version control
├── .kiro/              # Kiro AI assistant configuration
│   └── steering/       # AI guidance documents
├── .gitignore          # Python-specific gitignore
├── LICENSE             # Apache License 2.0
└── README.md           # Project description
```

## Recommended Structure

As the project grows, follow this organization pattern:

```
TechnicalStockPrediction/
├── src/                      # Source code
│   └── technical_stock/      # Main package
│       ├── __init__.py
│       ├── indicators/       # Technical indicators (RSI, MACD, etc.)
│       ├── patterns/         # Chart pattern recognition
│       ├── prediction/       # Prediction models
│       └── data/             # Data fetching and processing
├── tests/                    # Test suite
│   ├── unit/
│   └── integration/
├── notebooks/                # Jupyter notebooks for analysis
├── data/                     # Data files (gitignored if large)
├── docs/                     # Documentation
├── requirements.txt          # Production dependencies
├── requirements-dev.txt      # Development dependencies
└── pyproject.toml            # Project metadata and build config
```

## Naming Conventions

- **Packages/Modules**: lowercase with underscores (`technical_stock`, `chart_patterns`)
- **Classes**: PascalCase (`StockPredictor`, `TechnicalIndicator`)
- **Functions/Variables**: lowercase with underscores (`calculate_rsi`, `stock_data`)
- **Constants**: uppercase with underscores (`MAX_LOOKBACK_DAYS`, `DEFAULT_THRESHOLD`)

## File Organization

- Keep related functionality together in modules
- Separate data processing, analysis, and prediction logic
- Place reusable utilities in dedicated utility modules
- Store configuration in separate config files
- Keep notebooks for exploratory analysis and visualization
