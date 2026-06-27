# Product Overview

## Bullish Stock Scanner

A full-stack MVP application for identifying potentially bullish stocks through technical analysis. The system combines a Python FastAPI backend with a React frontend to provide real-time stock analysis based on five core technical indicators.

## Purpose

Analyze technical indicators and chart patterns to identify stocks with bullish potential, helping traders and investors make informed decisions based on technical analysis. The system provides:

- **Automated Scanning**: Batch analysis of multiple tickers in a single scan
- **Market Context**: Overall market regime classification for contextualized analysis
- **Quantified Signals**: Numerical scoring (0-100) based on multiple bullish indicators
- **Ranked Results**: Stocks sorted by bullish potential for quick decision-making
- **Real-time Analysis**: On-demand scanning with current market data

## Core Features

### Technical Analysis
- **5 Core Indicators**: SMA(50), EMA(20), MACD, Volume, Relative Strength
- **Rule-Based Scoring**: Transparent 100-point scoring system
- **Market Regime Detection**: Bullish/bearish/neutral market classification using SPY index
- **Comprehensive Signals**: Individual signal breakdown for each ticker

### User Experience
- **Web Interface**: Clean, professional React UI with Cloudscape Design System components
- **REST API**: Programmatic access via FastAPI endpoints
- **Interactive Documentation**: Automatic Swagger UI at `/docs`
- **Real-time Feedback**: Loading states and error handling
- **Ranked Display**: Tickers ordered by bullish score with detailed breakdown

### Performance
- **Concurrent Processing**: Up to 5 simultaneous API requests
- **Smart Caching**: In-memory cache per scan session
- **Error Resilience**: Continues processing if individual tickers fail
- **Fast Response**: Typical scan of 50 tickers completes in 5-6 seconds

## Target Users

1. **Day Traders**: Quick identification of bullish opportunities
2. **Swing Traders**: Technical analysis for multi-day positions
3. **Retail Investors**: Data-driven stock selection assistance
4. **Developers**: API access for integration with trading systems
5. **Analysts**: Batch analysis for research and backtesting

## MVP Scope (2-Hour Development Timeline)

### In Scope
- 5 core technical indicators (SMA, EMA, MACD, Volume, RS)
- Simple rule-based scoring (no ML)
- Market regime analysis
- FastAPI backend with Swagger docs
- React frontend with Cloudscape Design System
- In-memory caching (no persistent storage)
- Basic error handling
- Unit and property-based tests

### Out of Scope (Future Phases)
- Advanced indicators (RSI, Bollinger Bands, Stochastic)
- Chart pattern recognition (head & shoulders, cup & handle)
- Machine learning scoring models
- Historical backtesting capabilities
- User authentication and accounts
- Persistent storage and scan history
- Real-time price updates via WebSocket
- Custom indicator weights
- Multi-timeframe analysis
- Mobile application

## Technical Approach

### Architecture
- **Backend**: Python 3.10+ with FastAPI framework
- **Frontend**: React 18+ with TypeScript and Cloudscape Design System (`@cloudscape-design/components`)
- **API Design**: RESTful with automatic OpenAPI documentation
- **Testing**: Comprehensive coverage with property-based testing using hypothesis
- **Deployment**: Standard Python/Node deployment (Docker ready for future)

### Key Design Decisions

1. **FastAPI over Flask**: Automatic API docs, async support, modern Python features
2. **Property-Based Testing**: Mathematical correctness verification for indicators
3. **In-Memory Cache**: Simple MVP solution, Redis migration path for production
4. **Rule-Based Scoring**: Transparent, explainable, no ML complexity for MVP
5. **Cloudscape Design System**: Consistent, professional AWS-style design with minimal custom CSS
6. **Modular Architecture**: Clean separation for easy testing and future enhancements

## Success Metrics

### MVP Success Criteria
- Scan completes in <15 seconds for 50 tickers
- >80% test coverage
- All 5 indicators calculate correctly (verified by property tests)
- Frontend displays results with no data loss
- API handles errors gracefully without crashes

### Future Success Metrics
- User engagement: scans per day
- Accuracy: correlation between high scores and actual price movement
- Performance: p95 response time <10s for 100 tickers
- Reliability: 99.9% uptime

## Roadmap

### Phase 1: MVP (Current)
Core functionality with 5 indicators, basic UI, API, and testing

### Phase 2: Enhanced Analysis
- Add 5 more technical indicators (RSI, Bollinger Bands, etc.)
- Implement basic chart pattern recognition
- Add historical backtesting

### Phase 3: Intelligence
- Machine learning scoring model
- Predictive accuracy tracking
- Custom indicator weights

### Phase 4: Platform
- User authentication and accounts
- Saved watchlists
- Alert notifications
- Persistent scan history
- Real-time updates via WebSocket

### Phase 5: Advanced
- Multi-timeframe analysis
- Options flow integration
- News sentiment analysis
- Mobile application

## Competitive Advantage

- **Open Source**: Apache 2.0 license for transparency and customization
- **API-First**: Full programmatic access for automation
- **Property-Based Testing**: Mathematical correctness guarantees
- **Modern Stack**: Fast, type-safe, maintainable codebase
- **Clear Methodology**: Transparent scoring rules, no black box

## License

Apache License 2.0 - Open source project with permissive licensing for commercial and non-commercial use.
