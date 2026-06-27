# MCP Massive Financial Data API Guide

## Overview

The MCP Massive server provides access to comprehensive financial market data through Polygon.io's API. It offers stock prices, options data, aggregates, trades, quotes, company fundamentals, and more. This guide documents patterns discovered through testing and provides best practices for the Bullish Stock Scanner project.

## Authentication

The API key is configured through the MCP server settings at `~/.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "massive": {
      "command": "mcp_massive",
      "env": {
        "MASSIVE_API_KEY": "${POLYGON_TOKEN}"
      }
    }
  }
}
```

The `POLYGON_TOKEN` environment variable should contain your Polygon.io API key. Different plan tiers provide access to different endpoints and data frequencies.

## Core Tools

### 1. mcp_massive_search_endpoints

**Purpose**: Discover available API endpoints and local functions using natural language queries.


**Parameters**:
- `query` (required): Natural language search string (max 200 chars)
- `scope` (optional): "all" (default), "endpoints", or "functions"

**Returns**: List of matching endpoints with:
- Endpoint name and category
- HTTP method and URL pattern
- Brief description
- Documentation URL (for endpoints)
- Function signature and parameters (for functions)

**Examples**:

```python
# Search for stock price endpoints
mcp_massive_search_endpoints(query="stock price aggregates bars")

# Search only for technical indicator functions
mcp_massive_search_endpoints(query="sma ema moving average", scope="functions")

# Search for options data
mcp_massive_search_endpoints(query="options chain contracts")

# Search for company fundamentals
mcp_massive_search_endpoints(query="company financials earnings revenue")
```

**Best Practices**:
- Always search before making API calls to find the right endpoint
- Use scope="functions" to discover post-processing functions for the apply parameter
- Keep queries under 200 characters
- Use multiple targeted searches instead of one broad query


### 2. mcp_massive_get_endpoint_docs

**Purpose**: Get detailed parameter documentation for a specific endpoint.

**Parameters**:
- `url` (required): Documentation URL from search_endpoints results

**Returns**: Endpoint pattern and table of query parameters with types, requirements, and descriptions.

**Example**:

```python
# First search for the endpoint
results = mcp_massive_search_endpoints(query="custom bars aggregates")

# Then get detailed docs using the docs URL from results
docs = mcp_massive_get_endpoint_docs(
    url="https://massive.com/docs/rest/stocks/aggregates/custom-bars.md"
)
```

**Usage Pattern**: Always call this after search_endpoints to understand required vs optional parameters before making API calls.

### 3. mcp_massive_call_api

**Purpose**: Fetch financial data from the API with optional post-processing and storage.

**Parameters**:
- `method` (required): "GET" (only GET supported)
- `path` (required): API endpoint path (e.g., `/v2/aggs/ticker/AAPL/range/1/day/2024-01-01/2024-01-31`)
- `params` (optional): Query parameters as dictionary
- `store_as` (optional): Table name to store results for SQL querying
- `apply` (optional): List of function steps for post-processing (max 20 steps)
- `api_key` (optional): Override default API key


**Returns**: CSV data or confirmation message if stored. Includes pagination hint if more data available.

**Basic Examples**:

```python
# Fetch daily AAPL prices for January 2024
mcp_massive_call_api(
    method="GET",
    path="/v2/aggs/ticker/AAPL/range/1/day/2024-01-01/2024-01-31",
    params={"adjusted": True, "limit": 50, "sort": "asc"}
)

# Store data for later SQL querying
mcp_massive_call_api(
    method="GET",
    path="/v2/aggs/ticker/MSFT/range/1/day/2024-01-01/2024-01-31",
    params={"adjusted": True, "limit": 50, "sort": "asc"},
    store_as="msft_prices"
)
```

**Advanced: Using the apply Parameter**

The `apply` parameter enables post-processing with technical indicators and calculations. Each step has:
- `function`: Function name (from search with scope="functions")
- `inputs`: Dictionary of parameter names to column names or literal values
- `output`: New column name for the result

```python
# Calculate SMA, EMA, and returns in one request
mcp_massive_call_api(
    method="GET",
    path="/v2/aggs/ticker/AAPL/range/1/day/2023-12-01/2024-01-31",
    params={"adjusted": True, "limit": 100, "sort": "asc"},
    apply=[
        {"function": "sma", "inputs": {"column": "c", "window": 20}, "output": "sma_20"},
        {"function": "ema", "inputs": {"column": "c", "window": 12}, "output": "ema_12"},
        {"function": "simple_return", "inputs": {"column": "c"}, "output": "returns"}
    ]
)
```


**Pagination Handling**:

When results exceed the limit, a pagination hint appears at the end of output:

```
Next page available. To fetch, call call_api with path="/v3/reference/tickers" 
and params={"cursor": "YWN0aXZlPXRydWUmYXA9MTAmYXM9JmxpbWl0PTEwJm1hcmtldD1zdG9ja3Mmc29ydD10aWNrZXI"}
```

Use the provided cursor parameter to fetch the next page:

```python
# Fetch next page
mcp_massive_call_api(
    method="GET",
    path="/v3/reference/tickers",
    params={"cursor": "YWN0aXZlPXRydWUmYXA9MTAmYXM9JmxpbWl0PTEwJm1hcmtldD1zdG9ja3Mmc29ydD10aWNrZXI"}
)
```

### 4. mcp_massive_query_data

**Purpose**: Query stored data using SQL (SQLite engine).

**Parameters**:
- `sql` (required): SQL query or special command
- `apply` (optional): List of function steps for post-processing

**Special Commands**:
- `SHOW TABLES`: List all stored DataFrames with row counts and age
- `DESCRIBE <table>`: Show table schema (columns and types)
- `DROP TABLE <table>`: Remove a stored table

**Note**: Tables auto-expire after 1 hour.


**Examples**:

```python
# List all stored tables
mcp_massive_query_data(sql="SHOW TABLES")

# Check table schema
mcp_massive_query_data(sql="DESCRIBE aapl_prices")

# Basic query
mcp_massive_query_data(
    sql="SELECT c, v, vw FROM aapl_prices ORDER BY c DESC LIMIT 5"
)

# Complex query with aggregations
mcp_massive_query_data(sql="""
SELECT 
  'AAPL' as ticker,
  AVG(c) as avg_close,
  MAX(h) as max_high,
  MIN(l) as min_low,
  SUM(v) as total_volume
FROM aapl_prices
UNION ALL
SELECT 
  'MSFT' as ticker,
  AVG(c) as avg_close,
  MAX(h) as max_high,
  MIN(l) as min_low,
  SUM(v) as total_volume
FROM msft_prices
""")

# Query with apply parameter for post-processing
mcp_massive_query_data(
    sql="SELECT c, v FROM aapl_prices ORDER BY t",
    apply=[
        {"function": "simple_return", "inputs": {"column": "c"}, "output": "daily_return"},
        {"function": "ema", "inputs": {"column": "c", "window": 12}, "output": "ema_12"}
    ]
)
```


**SQL Capabilities**:
- Standard SQLite SQL syntax
- Window functions (ROW_NUMBER, RANK, LAG, LEAD, etc.)
- CTEs (Common Table Expressions)
- Subqueries (scalar and table)
- Aggregations (SUM, AVG, COUNT, MIN, MAX)
- ILIKE for case-insensitive pattern matching
- Complex expressions and calculations

## Available Functions for Apply Parameter

### Technical Indicators

| Function | Description | Parameters |
|----------|-------------|------------|
| `sma` | Simple Moving Average | `column` (str), `window` (int) |
| `ema` | Exponential Moving Average | `column` (str), `window` (int) |

### Returns Calculations

| Function | Description | Parameters |
|----------|-------------|------------|
| `simple_return` | Percentage return: (p_t - p_{t-1}) / p_{t-1} | `column` (str) |
| `log_return` | Logarithmic return: log(p_t / p_{t-1}) | `column` (str) |
| `cumulative_return` | Cumulative return: (1 + r).cumprod() - 1 | `column` (str) |
| `sharpe_ratio` | Rolling Sharpe ratio | `column` (str), `window` (int), `rf` (float, optional) |
| `sortino_ratio` | Rolling Sortino ratio | `column` (str), `window` (int), `rf` (float, optional) |

### Options Greeks (Black-Scholes)

| Function | Description | Parameters |
|----------|-------------|------------|
| `bs_price` | Option price | `S`, `K`, `T`, `r`, `sigma`, `option_type` (optional: "call"/"put") |
| `bs_delta` | Delta | `S`, `K`, `T`, `r`, `sigma`, `option_type` (optional) |
| `bs_gamma` | Gamma | `S`, `K`, `T`, `r`, `sigma` |
| `bs_theta` | Daily theta | `S`, `K`, `T`, `r`, `sigma`, `option_type` (optional) |
| `bs_vega` | Vega per 1% vol change | `S`, `K`, `T`, `r`, `sigma` |
| `bs_rho` | Rho per 1% rate change | `S`, `K`, `T`, `r`, `sigma`, `option_type` (optional) |


**Parameter Types for Functions**:
- `column`: Column name from the DataFrame (string)
- `col_or_lit`: Either a column name (string) or a literal value (number)
- `literal`: A numeric or string literal value
- `literal_str`: A string literal value

## Common Endpoints for Stock Scanner

### Price Data (Aggregates/OHLCV)

**Custom Bars** - Most flexible for historical data:
```
GET /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}
```
Parameters: `adjusted`, `sort`, `limit`

**Previous Day Bar** - Quick access to yesterday's data:
```
GET /v2/aggs/ticker/{ticker}/prev
```
Parameters: `adjusted`

**Daily Market Summary** - All US stocks for a date:
```
GET /v2/aggs/grouped/locale/us/market/stocks/{date}
```
Parameters: `adjusted`, `include_otc`

### Ticker Information

**All Tickers** - Search and list tickers:
```
GET /v3/reference/tickers
```
Parameters: `ticker`, `type`, `market`, `active`, `search`, `limit`, `sort`

**Market Status** - Check if markets are open:
```
GET /v1/marketstatus/now
```

### Volume Analysis

Volume data is included in aggregate endpoints as the `v` column.


### Options Data

**Option Chain Snapshot** - All contracts for an underlying:
```
GET /v3/snapshot/options/{underlyingAsset}
```

**All Contracts** - Search options contracts:
```
GET /v3/reference/options/contracts
```
Parameters: `underlying_ticker`, `contract_type`, `expiration_date`, `strike_price`

### Company Fundamentals

**Income Statements**:
```
GET /stocks/financials/v1/income-statements
```

**Balance Sheets**:
```
GET /stocks/financials/v1/balance-sheets
```

**Note**: Some endpoints require higher-tier subscription plans.

## Data Structure Reference

### Aggregate (OHLCV) Columns

| Column | Description |
|--------|-------------|
| `o` | Open price |
| `h` | High price |
| `c` | Close price |
| `l` | Low price |
| `v` | Volume (number of shares) |
| `vw` | Volume-weighted average price (VWAP) |
| `t` | Timestamp (Unix milliseconds) |
| `n` | Number of transactions |


## Workflow Patterns

### Pattern 1: Simple Data Fetch

Best for one-time queries where you need raw data immediately.

```python
# 1. Search for endpoint
search_results = mcp_massive_search_endpoints(query="daily stock prices")

# 2. Get documentation
docs = mcp_massive_get_endpoint_docs(url="https://massive.com/docs/rest/stocks/aggregates/custom-bars.md")

# 3. Fetch data
data = mcp_massive_call_api(
    method="GET",
    path="/v2/aggs/ticker/AAPL/range/1/day/2024-01-01/2024-01-31",
    params={"adjusted": True, "limit": 50, "sort": "asc"}
)
```

### Pattern 2: Store and Query

Best for analyzing multiple tickers or doing complex calculations across datasets.

```python
# 1. Fetch and store multiple tickers
mcp_massive_call_api(
    method="GET",
    path="/v2/aggs/ticker/AAPL/range/1/day/2024-01-01/2024-01-31",
    params={"adjusted": True, "sort": "asc"},
    store_as="aapl_prices"
)

mcp_massive_call_api(
    method="GET",
    path="/v2/aggs/ticker/MSFT/range/1/day/2024-01-01/2024-01-31",
    params={"adjusted": True, "sort": "asc"},
    store_as="msft_prices"
)

# 2. Query across datasets
comparison = mcp_massive_query_data(sql="""
SELECT 
  'AAPL' as ticker, AVG(c) as avg_price, SUM(v) as total_volume
FROM aapl_prices
UNION ALL
SELECT 
  'MSFT' as ticker, AVG(c) as avg_price, SUM(v) as total_volume
FROM msft_prices
""")
```


### Pattern 3: Apply Technical Indicators

Best for getting pre-calculated indicators without manual computation.

```python
# Fetch with multiple technical indicators calculated server-side
data = mcp_massive_call_api(
    method="GET",
    path="/v2/aggs/ticker/AAPL/range/1/day/2023-12-01/2024-01-31",
    params={"adjusted": True, "limit": 100, "sort": "asc"},
    apply=[
        {"function": "sma", "inputs": {"column": "c", "window": 20}, "output": "sma_20"},
        {"function": "sma", "inputs": {"column": "c", "window": 50}, "output": "sma_50"},
        {"function": "ema", "inputs": {"column": "c", "window": 12}, "output": "ema_12"},
        {"function": "ema", "inputs": {"column": "c", "window": 26}, "output": "ema_26"},
        {"function": "simple_return", "inputs": {"column": "c"}, "output": "returns"},
        {"function": "sma", "inputs": {"column": "v", "window": 20}, "output": "avg_volume"}
    ],
    store_as="aapl_with_indicators"
)

# Then query for signals
signals = mcp_massive_query_data(sql="""
SELECT 
  t,
  c,
  sma_20,
  sma_50,
  CASE 
    WHEN c > sma_20 AND sma_20 > sma_50 THEN 'Bullish'
    WHEN c < sma_20 AND sma_20 < sma_50 THEN 'Bearish'
    ELSE 'Neutral'
  END as signal
FROM aapl_with_indicators
ORDER BY t DESC
LIMIT 10
""")
```


### Pattern 4: Batch Processing with Pagination

Best for scanning large numbers of tickers.

```python
# 1. Get list of tickers
page1 = mcp_massive_call_api(
    method="GET",
    path="/v3/reference/tickers",
    params={"active": True, "market": "stocks", "limit": 100}
)

# 2. If pagination hint appears, continue fetching
# Extract cursor from hint and fetch next page
page2 = mcp_massive_call_api(
    method="GET",
    path="/v3/reference/tickers",
    params={"cursor": "cursor_value_from_hint"}
)

# 3. Process each ticker
# (Iterate through results and fetch data for each)
```

## Error Handling Patterns

### HTTP Errors

**403 NOT_AUTHORIZED**: Endpoint requires a higher subscription tier.
```
Error [AUTH]: HTTP 403 — {"status":"NOT_AUTHORIZED","message":"You are not entitled to this data..."}
```

**400 Bad Request**: Invalid parameters (e.g., malformed dates).
```
Error [HTTP]: HTTP 400 — {"status":"ERROR","error":"Could not parse the time parameter: 'from'..."}
```

**Handling**:
- Check subscription plan limits at polygon.io/pricing
- Validate date formats (YYYY-MM-DD) before API calls
- Use get_endpoint_docs to verify required parameters


### No Data Available

If a ticker has no data for the requested period, the response may only contain metadata:
```
ticker,adjusted
INVALIDTICKER123,True
```

**Handling**: Check if response contains expected columns (o, h, l, c, v) before processing.

### Table Expiration

Tables stored via `store_as` expire after 1 hour. Use `SHOW TABLES` to check age.

**Handling**: Re-fetch data if needed, or design workflows to complete within the 1-hour window.

## Best Practices

### 1. Always Search First

Don't guess endpoint URLs. Use `search_endpoints` to find the correct path and parameters.

```python
# Good
results = mcp_massive_search_endpoints(query="stock aggregates")
# Review results, then use the documented endpoint

# Bad
mcp_massive_call_api(path="/v2/stocks/AAPL/bars")  # Guessing - likely wrong
```

### 2. Use store_as for Multi-Ticker Analysis

When analyzing multiple tickers, store each in a table and use SQL for comparisons.

```python
# Efficient: Store and query
for ticker in ["AAPL", "MSFT", "GOOGL"]:
    mcp_massive_call_api(
        path=f"/v2/aggs/ticker/{ticker}/range/1/day/2024-01-01/2024-01-31",
        store_as=f"{ticker.lower()}_prices"
    )

# Then query all at once
results = mcp_massive_query_data(sql="SELECT ...")
```


### 3. Leverage Apply for Server-Side Calculations

Calculate technical indicators server-side instead of fetching raw data and computing locally.

```python
# Efficient: Calculate indicators in one request
mcp_massive_call_api(
    path="/v2/aggs/ticker/AAPL/range/1/day/2024-01-01/2024-01-31",
    apply=[
        {"function": "sma", "inputs": {"column": "c", "window": 20}, "output": "sma_20"},
        {"function": "simple_return", "inputs": {"column": "c"}, "output": "returns"}
    ]
)

# Less efficient: Fetch raw data, then calculate locally in Python
```

### 4. Validate Dates Before API Calls

Use YYYY-MM-DD format. Invalid dates return 400 errors.

```python
# Good
from datetime import datetime
date_str = datetime.now().strftime("%Y-%m-%d")

# Bad
date_str = "01/31/2024"  # Wrong format
date_str = "2024-13-01"  # Invalid month
```

### 5. Handle Pagination for Large Datasets

Always check for pagination hints and fetch all pages when needed.

```python
def fetch_all_pages(path, params):
    all_data = []
    while True:
        result = mcp_massive_call_api(method="GET", path=path, params=params)
        all_data.append(result)
        
        # Check for pagination hint in result
        if "Next page available" not in result:
            break
            
        # Extract cursor from hint and update params
        # (Parse the hint to get cursor value)
        
    return all_data
```


### 6. Use Appropriate Limits

Balance data completeness with API efficiency:
- Default limit is often 5000
- Max limit varies by endpoint (check docs)
- For aggregates, max is typically 50,000

```python
# For scanning recent data
params={"limit": 30}  # Last 30 days

# For comprehensive analysis
params={"limit": 5000}  # Use default or higher
```

### 7. Sort Results Consistently

Always specify `sort` parameter for predictable ordering:
- `asc`: Oldest first (good for time-series analysis)
- `desc`: Newest first (good for recent data)

```python
# For indicator calculations (need chronological order)
params={"sort": "asc"}

# For latest snapshot
params={"sort": "desc", "limit": 1}
```

## MCP Tools vs Direct API Comparison

### When to Use MCP Tools

✅ **Use MCP Massive tools when**:
- You need quick data exploration and analysis
- You want server-side technical indicator calculations
- You're prototyping or testing strategies
- You need to query across multiple tickers with SQL
- You want to avoid managing HTTP clients and error handling
- You're working in an environment with MCP support (like Kiro)

### When to Use Direct API Calls

✅ **Use direct Polygon.io API when**:
- Building a production application
- Need WebSocket real-time data streams
- Require fine-grained control over retries and rate limiting
- Need to cache responses persistently
- Working in environments without MCP support
- Need to integrate with existing Python/Node libraries


### Feature Comparison

| Feature | MCP Massive | Direct API |
|---------|-------------|------------|
| HTTP client setup | ✅ Built-in | ❌ Manual |
| Error handling | ✅ Automatic | ❌ Manual |
| Technical indicators | ✅ Server-side | ❌ Client-side |
| SQL queries | ✅ Built-in | ❌ Manual (pandas/SQL) |
| Real-time data | ❌ Limited | ✅ WebSocket |
| Pagination | ✅ Automatic hints | ❌ Manual cursor handling |
| Rate limiting | ✅ Handled by MCP | ❌ Manual throttling |
| Caching | ⚠️ 1-hour temp tables | ✅ Persistent (Redis, etc.) |
| Production ready | ⚠️ Depends on use case | ✅ Full control |

## Rate Limits and Performance

### Polygon.io Rate Limits (varies by plan)

- **Free**: 5 requests/minute
- **Starter**: 100 requests/minute
- **Developer**: 1,000 requests/minute
- **Advanced+**: Higher limits and unlimited for some endpoints

### MCP Massive Behavior

- The MCP server handles rate limiting internally
- Failed requests due to rate limits will return errors
- No built-in retry mechanism (must handle manually)

### Optimization Tips

1. **Batch by date range**: Fetch longer periods in single requests
2. **Use store_as**: Avoid re-fetching the same data
3. **Leverage apply**: Calculate indicators server-side
4. **Cache ticker lists**: Fetch and store ticker metadata once
5. **Monitor table age**: Check `SHOW TABLES` output for expiration


## Complete Example: Bullish Stock Scanner

Here's a complete workflow for scanning stocks with the MCP Massive tools:

```python
# Step 1: Get list of active stock tickers
tickers_data = mcp_massive_call_api(
    method="GET",
    path="/v3/reference/tickers",
    params={
        "active": True,
        "market": "stocks",
        "type": "CS",  # Common Stock
        "limit": 50
    }
)

# Step 2: Fetch price data with indicators for each ticker
# Example with AAPL
aapl_data = mcp_massive_call_api(
    method="GET",
    path="/v2/aggs/ticker/AAPL/range/1/day/2024-01-01/2024-01-31",
    params={"adjusted": True, "sort": "asc", "limit": 100},
    apply=[
        {"function": "sma", "inputs": {"column": "c", "window": 50}, "output": "sma_50"},
        {"function": "ema", "inputs": {"column": "c", "window": 20}, "output": "ema_20"},
        {"function": "simple_return", "inputs": {"column": "c"}, "output": "returns"},
        {"function": "sma", "inputs": {"column": "v", "window": 20}, "output": "avg_volume"}
    ],
    store_as="aapl_analysis"
)

# Step 3: Fetch SPY for market regime
spy_data = mcp_massive_call_api(
    method="GET",
    path="/v2/aggs/ticker/SPY/range/1/day/2024-01-01/2024-01-31",
    params={"adjusted": True, "sort": "asc"},
    apply=[
        {"function": "sma", "inputs": {"column": "c", "window": 200}, "output": "sma_200"}
    ],
    store_as="spy_regime"
)


# Step 4: Query for bullish signals
bullish_signals = mcp_massive_query_data(sql="""
SELECT 
  t,
  c as price,
  sma_50,
  ema_20,
  v as volume,
  avg_volume,
  returns,
  CASE 
    WHEN c > sma_50 THEN 1 ELSE 0 
  END as above_sma50,
  CASE 
    WHEN c > ema_20 THEN 1 ELSE 0 
  END as above_ema20,
  CASE 
    WHEN v > avg_volume * 1.5 THEN 1 ELSE 0 
  END as high_volume,
  CASE 
    WHEN returns > 0 THEN 1 ELSE 0 
  END as positive_return
FROM aapl_analysis
WHERE sma_50 IS NOT NULL AND ema_20 IS NOT NULL
ORDER BY t DESC
LIMIT 1
""")

# Step 5: Calculate bullish score
# This would be done for each ticker, then ranked
# Score = above_sma50 * 20 + above_ema20 * 20 + high_volume * 30 + positive_return * 30
```

## Tips and Gotchas

### ✅ Do's

1. **Search before you fetch**: Use `search_endpoints` to find the right endpoint
2. **Validate dates**: Always use YYYY-MM-DD format
3. **Store for analysis**: Use `store_as` when you need to query data
4. **Apply indicators**: Leverage server-side calculations for efficiency
5. **Check table expiry**: Monitor age_seconds in SHOW TABLES output
6. **Handle pagination**: Look for pagination hints in responses
7. **Sort chronologically**: Use `sort=asc` for indicator calculations


### ❌ Don'ts

1. **Don't guess endpoint URLs**: Always search first
2. **Don't ignore auth errors**: Check your subscription tier for endpoint access
3. **Don't fetch raw data when apply works**: Use server-side calculations
4. **Don't forget to handle empty results**: Check for data columns before processing
5. **Don't rely on tables > 1 hour**: Re-fetch if needed
6. **Don't use wrong date formats**: Stick to YYYY-MM-DD
7. **Don't assume data exists**: Invalid tickers return empty results

### Common Pitfalls

**Pitfall 1: Missing data for moving averages**
```python
# Problem: SMA(20) requires 20 data points
# First 19 rows will have NULL for sma_20

# Solution: Fetch more data than your window size
# For SMA(50), fetch at least 50 days
```

**Pitfall 2: Timestamp format**
```python
# Timestamps are Unix milliseconds, not seconds
# t = 1704171600000 (milliseconds)

# To convert in SQL:
# datetime(t/1000, 'unixepoch') for human-readable dates
```

**Pitfall 3: Volume comparison without normalization**
```python
# Problem: Comparing raw volume across different stocks
# AAPL volume: 80M shares
# Small cap volume: 100K shares

# Solution: Use relative volume (current / average)
# Or use apply parameter with sma on volume column
```


**Pitfall 4: Adjusted vs unadjusted prices**
```python
# Use adjusted=True for historical analysis
# This accounts for stock splits and dividends
params={"adjusted": True}

# Use adjusted=False only if you need raw historical prices
```

**Pitfall 5: Function parameter types**
```python
# Correct: String inputs reference column names
{"function": "sma", "inputs": {"column": "c", "window": 20}}

# Correct: Numeric inputs are literals
{"function": "sharpe_ratio", "inputs": {"column": "returns", "window": 10, "rf": 0.02}}

# Wrong: Quoting numeric literals
{"function": "sma", "inputs": {"column": "c", "window": "20"}}  # Error
```

## Quick Reference

### Most Common Endpoints

```
# Stock daily prices
/v2/aggs/ticker/{ticker}/range/1/day/{from}/{to}

# Previous day
/v2/aggs/ticker/{ticker}/prev

# List tickers
/v3/reference/tickers

# Market status
/v1/marketstatus/now
```

### Most Useful Functions

```python
# Moving averages
{"function": "sma", "inputs": {"column": "c", "window": 20}, "output": "sma_20"}
{"function": "ema", "inputs": {"column": "c", "window": 12}, "output": "ema_12"}

# Returns
{"function": "simple_return", "inputs": {"column": "c"}, "output": "returns"}
{"function": "log_return", "inputs": {"column": "c"}, "output": "log_returns"}

# Risk metrics
{"function": "sharpe_ratio", "inputs": {"column": "returns", "window": 20}, "output": "sharpe"}
```


### Common SQL Patterns

```sql
-- Latest values for a ticker
SELECT * FROM ticker_data ORDER BY t DESC LIMIT 1

-- Calculate percentage changes
SELECT 
  c,
  LAG(c) OVER (ORDER BY t) as prev_close,
  (c - LAG(c) OVER (ORDER BY t)) / LAG(c) OVER (ORDER BY t) * 100 as pct_change
FROM ticker_data

-- Compare to moving average
SELECT 
  c,
  sma_20,
  (c - sma_20) / sma_20 * 100 as distance_from_sma
FROM ticker_data
WHERE sma_20 IS NOT NULL

-- Aggregate across multiple tickers
SELECT 
  'AAPL' as ticker, AVG(c) as avg_price FROM aapl_prices
UNION ALL
SELECT 
  'MSFT' as ticker, AVG(c) as avg_price FROM msft_prices
ORDER BY avg_price DESC
```

## Integration with Bullish Stock Scanner

### Recommended Approach

For the Bullish Stock Scanner MVP, **use direct API calls** instead of MCP Massive:

**Reasons**:
1. **Production readiness**: Direct API gives full control over caching, retries, rate limiting
2. **Existing architecture**: Project already has API client infrastructure
3. **Consistency**: Keep all data fetching in one place (api_client.py)
4. **Testing**: Easier to mock and test with standard HTTP libraries
5. **Deployment**: No MCP server dependency in production

### When to Use MCP Massive for This Project

✅ **Development & Testing**:
- Quick data exploration during development
- Validating indicator calculations
- Prototyping new features
- Ad-hoc analysis during debugging

✅ **Future Features**:
- Interactive analysis dashboard
- Backtesting workbench
- Research notebooks integration


### Hybrid Approach Example

Use MCP for exploration, then implement in production code:

```python
# 1. Explore with MCP Massive
mcp_massive_call_api(
    method="GET",
    path="/v2/aggs/ticker/AAPL/range/1/day/2024-01-01/2024-01-31",
    apply=[
        {"function": "sma", "inputs": {"column": "c", "window": 50}, "output": "sma_50"}
    ]
)
# Review output, validate logic

# 2. Implement in api_client.py
async def fetch_historical_prices(ticker: str, from_date: str, to_date: str):
    """Fetch and cache historical price data"""
    url = f"{BASE_URL}/v2/aggs/ticker/{ticker}/range/1/day/{from_date}/{to_date}"
    params = {"adjusted": True, "sort": "asc", "limit": 5000}
    # Use httpx with retry logic...
    
# 3. Calculate indicators in indicator_calculator.py
def calculate_sma(prices: List[float], window: int) -> List[Optional[float]]:
    """Calculate simple moving average"""
    # Pure Python implementation with tests...
```

## Additional Resources

- **Polygon.io Documentation**: https://polygon.io/docs/stocks
- **MCP Massive GitHub**: Search for MCP server implementations
- **API Plans & Pricing**: https://polygon.io/pricing
- **Data Dictionary**: Check Polygon docs for complete field descriptions

## Testing Results Summary

Based on comprehensive testing:

✅ **Successfully Tested**:
- Endpoint search with natural language queries
- Function discovery for apply parameter
- Stock price data fetching (AAPL, MSFT)
- Data storage with store_as parameter
- SQL queries (simple, aggregations, joins, window functions)
- Apply parameter with 8+ functions (SMA, EMA, returns, Sharpe ratio)
- Pagination with cursor handling
- Error responses (auth errors, invalid dates)

⚠️ **Limitations Found**:
- Real-time endpoints require higher subscription tiers (403 errors)
- Tables expire after 1 hour
- No built-in retry mechanism for rate limits
- Apply parameter limited to 20 steps per request
- Invalid tickers return empty results (not errors)

---

**Document Version**: 1.0  
**Last Updated**: Based on testing session January 2024  
**Tested With**: Polygon.io API via MCP Massive server
