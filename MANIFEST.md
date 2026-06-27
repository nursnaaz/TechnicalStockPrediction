# TechnicalStockPrediction

Bullish stock scanner with backtesting. Scores stocks on technical indicators and validates predictions against historical data.

## Folders

- `backend/` - Python FastAPI server. Scoring engine, API client (Polygon.io), backtesting.
- `frontend/` - React + TypeScript + Cloudscape. Live scanner and backtest UI with confusion matrix.
- `.kiro/` - AI assistant config, specs, hooks, steering files.

## Key Files

- `backend/core/scoring_engine.py` - V2 gradient scoring + Stage 2 + Pattern bonus (RSI, ROC, proximity, MACD, SMA, EMA)
- `backend/core/indicator_calculator.py` - Computes 10 technical indicators
- `backend/core/stage_classifier.py` - Minervini Stage 2 classification (5 checks)
- `backend/core/pattern_detector.py` - VCP, Flat Base, Darvas Box, Tight Flag detection
- `backend/backtest/engine.py` - Backtesting engine (point-in-time, no look-ahead)
- `backend/backtest/metrics.py` - Confusion matrix, accuracy, precision, recall, F1
- `backend/api/backtest_endpoints.py` - POST /api/v1/backtest/single and /rolling
- `frontend/src/components/BacktestPanel.tsx` - Backtest UI with dynamic threshold sliders
- `ALL_HALAL_STOCKS.txt` - 150+ halal stock tickers for scanning
- `V2_DEVELOPMENT_PLAN.md` - Roadmap and Phoenix rules analysis

## Status

Built:
- V2 gradient scoring engine (RSI, ROC, breakout proximity, gradient SMA/EMA/volume)
- Backtesting framework with look-ahead bias prevention
- Confusion matrix (TP/FP/FN/TN) with accuracy/precision/recall/F1
- Backtest UI with date picker, sliders for threshold tuning
- Live scanner with Cloudscape components
- 205 backend tests passing

Not built yet:
- Pattern detection (VCP, Darvas, Flat Base)
- Stage 2 classification
- Machine learning scoring
- User auth, persistent history

## How to Run

```
cd backend && source .venv/bin/activate
uvicorn main:app --reload --port 8000

cd frontend && npm run dev

# Tests
cd backend && pytest
cd frontend && npx tsc --noEmit
```

## Optimal Backtest Settings

Score threshold: 50, Gain threshold: 5%, Horizon: 30 days.
Gives Precision=66%, Recall=58%, F1=62% on 150 trades (V2+Stage+Pattern engine).
For higher precision: Score≥67 gives Precision=76% but Recall=28%.
Use the UI sliders to find your preferred tradeoff.
