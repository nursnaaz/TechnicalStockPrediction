Kiro, I have an important requirement for you to build in a spec-driven way.

Basically, I have a requirement of building an application where it helps us in giving a ticker which is most bullish in the coming 30 days. I will be giving you the list of tickers you want to analyze, and out of those tickers you want to give me the bullish tickers based on the technical analyzer. I have a list of rules. Based on those, you want to implement these rules to build this particular application.

I want to build the application using FastAPI as a backend, and I want it to be React with Cloud Space library. I want the frontend UI library to be more professional and lightweight, and also it should be in a light way, that is in an Amazon kind of UI and Google kind of UI. Go through all those rules that I'm going to give to you, and whatever rules are given here I want to implement here now. Remember that I have only two hours to complete this project, and based on this limitation see what other things you can implement in the next couple of hours. Let's try to fix and complete this with a good FastAPI and React with Cloud Space

# Noor Technical Agent — Build Spec

 

> Implementation brief for a coding agent. Builds a single HTTP service that scans US equities daily and returns a ranked list of tickers expected to be **bullish over the next ~30 trading days**. Data: **Massive REST API** (formerly Polygon.io).

 

---

 

## 0. Vocabulary (read first)

 

- **Trading day** = a US session where the market is open (NYSE/Nasdaq). Holidays and weekends do not count. Whenever this spec says "N bars ago", "in last N sessions", or "N-day", it means **N trading days**, not calendar days.
- **as_of** = a single trading date in **US Eastern Time**. All bars used in any rule must satisfy `bar_date ≤ as_of`. No exceptions.
- **bar** = one OHLCV record for a single trading day, adjusted for splits and dividends (`adjusted=true` on every Massive call).
- **session** = synonym for trading day.
- **Look-ahead violation** = referencing any data with `bar_date > as_of`, directly or via a rolling statistic. This is the #1 silent bug. Every rule in this spec assumes strict no-look-ahead.

---

 

## 1. Mission

 

- Expose one primary endpoint that runs a full scan and returns the top N bullish candidates.
- Data source: **Massive REST API** at `https://api.massive.com`. Auth via `Authorization: Bearer <POLYGON_TOKEN>` header (the legacy Polygon API key works unchanged against the new Massive host).
- Horizon: 30 trading days forward.
- Output: ranked JSON list with entry zone, stop, targets, score, and pass/fail reasons.

---

 

## 2. Service contract

 

- `POST /scan` → triggers a full universe scan. Body (all optional):
- `as_of`: `"YYYY-MM-DD"` (default: latest closed trading day in ET)
- `top_n`: int (default `20`)
- `min_score`: int 0–100 (default `65`)
- `max_per_sector`: int (default `3`) — concentration cap
- `exclude`: `["TICKER", ...]` — names to skip (e.g. existing holdings)
- `request_id`: client-supplied idempotency key. If the same `request_id` arrives within 60s, return the cached prior result. Different `request_id` = new scan.
- `mode`: `"live"` (default) or `"backtest"` — backtest mode requires a historically-correct universe (see §22).
- `dry_run`: bool (default `false`)
- `GET /scan/{scan_id}` → fetch a previous scan result by ID.
- `GET /ticker/{symbol}?as_of=YYYY-MM-DD` → run the pipeline for one symbol; exposes every intermediate signal for debugging.
- `GET /health` → returns `{"status": "ok", "as_of": "..."}`.
- All responses are JSON. Persist each scan result with a UUID for retrieval.

### Error response schema (all non-2xx)

```json

{

  "error_code": "string",        // e.g. "UPSTREAM_RATE_LIMIT", "INVALID_AS_OF"

  "message": "human-readable",

  "request_id": "uuid",

  "partial_results_available": false,

  "details": { ... }

}

```

 

### Partial-failure policy

- If individual ticker fetches fail (network, 404, malformed data): drop that ticker, log it, continue the scan.
- If > 20% of universe fails: return `502` with `partial_results_available: true` and an option to fetch what was processed.
- If SPY (regime) fetch fails: hard fail. The scan is not valid without regime.

---

 

## 3. Massive API configuration

 

- Read API key from environment variable `POLYGON_TOKEN` (existing local secret name — same key works against the Massive host, no rotation needed).
- All requests: timeout 10s, 3 retries with exponential backoff, respect HTTP 429.
- Common response shape: `{ "status": "OK", "count": N, "results": [...], "request_id": "..." }`.
- Cap concurrent in-flight requests at **5** by default (safe across all paid plans); reduce to **1** on free tier. Make this plan-aware via config.
- Cache daily bars locally keyed by `(ticker, date)`; refresh only the delta on subsequent runs.
- Cache TTL: bars for dates earlier than the most recent close are immutable (cache forever, subject to manual flush for corporate-action re-adjustments). Bars for the current session expire at midnight ET.

---

 

## 4. Pipeline (execute in this order — fail-fast)

 

1. **Build universe** — list active US common stocks, then apply liquidity + IPO-age + halt filters.
2. **Pull market context** — SPY daily bars (≥ 1 year) → compute market regime.
3. **For each candidate ticker** (parallel, batched, concurrency-capped):
4. Pull daily bars (≥ 300 trading days back).
5. Resample to weekly bars locally.
6. Compute indicators.
7. Run hard filters → if any fail, exit with `signal=AVOID` and the failing rule recorded.
8. Classify stage → if not Stage 2, exit.
9. Detect patterns.
10. Compute composite score (Phoenix-style, 0–100).
11. Evaluate strategy confluence (Minervini + Stine + Elder weekly).
12. Apply extension/chase guardrail.
13. If passes all gates → produce candidate object with entry, stop, targets.
14. **Apply market regime overlay** — if SPY regime is bearish, multiply every candidate's final score by 0.65.
15. **Rank** all surviving candidates by final score.
16. **Apply concentration cap** — no more than `max_per_sector` candidates from one sector. When two compete, keep the higher final_score.
17. **Apply portfolio-level risk cap** — if cumulative `position_size_hint_pct_account` across returned candidates exceeds 12%, scale down proportionally and recompute hints.
18. **Apply optional post-rank screening hook** (e.g. halal / ESG / custom) if configured. Default: no-op.
19. **Apply `exclude` list** from the request.
20. **Return** top N where `final_score ≥ min_score`.

---

 

## 5. Universe construction

 

- Endpoint: `GET /v3/reference/tickers?market=stocks&type=CS&active=true&limit=1000` (paginate via `next_url`).
- Filter to primary exchange in `{XNYS, XNAS, ARCX, BATS}`.
- Pull latest grouped daily: `GET /v2/aggs/grouped/locale/us/market/stocks/{date}?adjusted=true` for the as_of date.
- Apply liquidity gate:
- Last close ≥ **$10**
- 20-day average dollar volume ≥ **$20M**
- Apply **IPO-age filter**: ticker must have ≥ **150 trading-day** history before `as_of`. Without it, SMA200 is undefined and basing structure is unreliable.
- Apply **halt / Reg SHO filter**: exclude any ticker whose latest snapshot reports a halted state, an LULD pause, or that appears on the day's Reg SHO threshold list. (Best-effort — log if data source unavailable.)
- Cache the qualifying universe daily.
- **Backtest mode (§22):** universe must be reconstructed as it existed at `as_of`, not today's universe.

---

 

## 6. Data pulls per ticker

 

- Daily bars: `GET /v2/aggs/ticker/{ticker}/range/1/day/{from}/{to}?adjusted=true&sort=asc&limit=50000`
- `from` = `as_of − 430 calendar days`, `to` = `as_of`
- Weekly bars: resample daily bars locally with these aggregation rules:
- `open` = first daily open of the week
- `high` = max daily high
- `low` = min daily low
- `close` = last daily close
- `volume` = **sum** of daily volumes
- A "week" runs Monday open → Friday close (ISO week). The current partial week is included only if at least one session has closed; otherwise use the prior completed week as the latest weekly bar.

---

 

## 7. Indicators to compute locally

 

All windows are in **trading days** unless suffixed `-wk` (weekly bars).

 

- **SMA**: 10, 20, 50, 150, 200
- **EMA**: 21d on SPY (regime), 13wk on each ticker (Elder)
- **MACD weekly**: 12/26/9 — store the histogram series
- **Volume average**: 20-day rolling
- **RVOL**: today's volume / 20d avg volume
- **52-week high & low**: rolling 252 trading days
- **RS line vs SPY**: ratio `close_stock / close_SPY`
- **RS rank**: percentile of stock's 63d return vs SPY's 63d return, **computed across the post-liquidity-filter universe at as_of**. Range 0–100.
- **RMV15**: rolling 15-bar stdev of daily log returns for this ticker, then percentile-ranked against **this same ticker's own** prior 60 bars of stdev values. 0 = tightest in 60 bars, 100 = widest.
- **ATR(14)**: standard Wilder's ATR. Used as a stop floor (see §16).
- **MA slope**: `(MA_today − MA_21_bars_ago) / MA_21_bars_ago`.

---

 

## 8. Hard filters — must pass ALL

 

| # | Rule | Threshold |

|---|---|---|

| H1 | Close above 200-day SMA | strictly `>` |

| H2 | Distance above 52-week low | `≥ 50%` |

| H3 | Distance below 52-week high | `≤ 35%` |

| H4 | No close below 50-day SMA in last 5 sessions | excluding ex-dividend gap-downs ≤ dividend amount |

| H5 | Earnings not within next 10 trading days | source via Massive 8-K filings + financials calendar; if both unavailable, **fail the scan with `MISSING_EARNINGS_DATA` rather than silently skip** |

 

If any H1–H4 fails → `signal=AVOID`, exit pipeline with the failing rule recorded.

 

---

 

## 9. Stage 2 classification — must be Stage 2

 

Stage 2 (institutional uptrend) requires ALL:

 

- `close > SMA50 > SMA200`
- SMA50 slope > **+0.3%**
- SMA200 slope ≥ **0%**
- `close ≥ 1.30 × low_52w`
- `close ≥ 0.75 × high_52w`

If not Stage 2 → exit pipeline.

 

---

 

## 10. Pattern detection (pick highest-confidence pattern)

 

Detect each; assign confidence using the explicit formulas below. Priority on tie: VCP > Darvas > Flat Base > Tight Flag.

 

### VCP (Volatility Contraction Pattern)

- Detection: ≥ 30 bars of history; up to 3 contractions, each ≥ 10% deep, each ≤ 50% the depth of the prior.
- Pivot = most recent recovery high.
- **Confirmed** when: `close > pivot` AND `today_volume ≥ 2.0 × vol_avg_20`.
- **Confidence** = clamp01( 0.40 × (contractions / 3) + 0.30 × volume_decline_quality + 0.30 × recency_factor )
- `volume_decline_quality` = `1 − (avg_vol_last_contraction / avg_vol_first_contraction)`, clamped [0, 1]
- `recency_factor` = `1 − (bars_since_last_contraction / 30)`, clamped [0, 1]

### Flat Base

- Detection: 20–120 bar sideways range, high-low range ≤ 15% of midpoint, volume in second half lower than first half.
- Pivot = base top.
- **Confirmed** when: `close > base_top` AND `today_volume ≥ 1.5 × vol_avg_20`.
- **Confidence** = clamp01( 0.50 × tightness + 0.30 × volume_dryup + 0.20 × duration_factor )
- `tightness` = `1 − (range_pct / 0.15)`
- `volume_dryup` = `1 − (avg_vol_second_half / avg_vol_first_half)`, clamped
- `duration_factor` = `min(bars_in_base, 60) / 60`

### Darvas Box

- Detection: prior 8% advance into the box; box length 3–40 bars, depth 1–15%.
- Pivot = box top.
- **Confirmed** when: `close > box_top` AND `today_volume ≥ 1.5 × box_avg_volume`.
- **Confidence** = clamp01( 0.50 × (1 − depth/0.15) + 0.50 × (box_avg_vol_decline) )

### Tight Flag

- Detection: flagpole ≥ 8% within last 15 bars; flag retraces ≤ 50% of pole; flag body ≤ 20 bars.
- Pivot = flag high.
- **Confirmed** when: `close > flag_high` on volume ≥ `1.5 × vol_avg_20`.
- **Confidence** = clamp01( 0.40 × pole_strength + 0.30 × (1 − retrace_pct/0.50) + 0.30 × (1 − flag_bars/20) )
- `pole_strength` = `min(pole_pct, 0.25) / 0.25`

`clamp01(x)` = `max(0, min(1, x))`.

 

If no pattern reaches confidence ≥ 0.4 → continue pipeline but cap pattern subscore at 5.

 

---

 

## 11. Composite score — Phoenix-style, 0–100

 

All weights and thresholds in this section are loaded from a config object (`config.scoring.*`) — no magic numbers in business logic.

 

```

score =

   0.40 × volume_subscore

 + 0.30 × structure_subscore

 + 0.20 × pattern_subscore

 + 0.10 × rs_subscore

```

 

**Volume subscore (0–40):**

- Volume trend (0–15): `avg_vol[-10:] / avg_vol[-20:-10] − 1`, clamped [0, 1], × 15
- Breakout volume (0–15): `today_vol / vol_avg_20`, linear up to 2.0× = 15
- Base dry-up (0–10): in last ~40 base bars, `(1 − avg_vol_second_half / avg_vol_first_half) × 10`

**Structure subscore (0–30):**

- 10 if `close > SMA200`
- 8 if `close > SMA20 > SMA50 > SMA200`
- +2 each for rising SMA20 / SMA50 / SMA200 (+1 for SMA10), cap 7
- 5 / 3 / 1 if `close` within 5% / 10% / 15% of SMA20

**Pattern subscore (0–20):**

- 12 if pattern confirmed
- `confidence × 5` (0–5)
- 3 if confidence ≥ 0.5

**RS subscore (0–10):**

- 10 if RS rank ≥ 80
- 7 if ≥ 70
- 4 if ≥ 50
- 0 otherwise

Map to signal:

- `score ≥ 70` → `BUY`
- `score ≥ 50` → `WATCH`
- else → `AVOID`

---

 

## 12. Strategy confluence — must hit ≥ 2 of 3

 

### A. Minervini Trend Template (need ≥ 6/10 checks)

1. `close > SMA150`
2. `close > SMA200`
3. `SMA150 > SMA200`
4. SMA200 rising over last 21 bars
5. `SMA50 > SMA150 AND SMA50 > SMA200`
6. `close > SMA50`
7. `close ≥ 1.30 × low_52w`
8. `close ≥ 0.75 × high_52w`
9. RS rank ≥ 70
10. EPS growth positive (skip if financials not wired; treat as pass when H5 ran clean)

**Entry trigger:** pass_count ≥ 6 AND Stage 2 AND `pct_from_pivot ≤ 5%` AND composite score ≥ 60.

 

### B. Stine 30-Week Superstock

- `close > SMA150`
- SMA150 rising over last 20 bars
- `(high_52w − close) / high_52w ≤ 25%`

**Entry trigger:** all three true.

 

### C. Elder Weekly Impulse

- From weekly bars:
- `weekly_EMA13_today > weekly_EMA13_yesterday`
- Weekly MACD histogram rising vs prior week
- Colors: GREEN (both rising), RED (both falling), BLUE (mixed)

**Entry trigger:** impulse just flipped to GREEN (prior week ≠ GREEN, this week = GREEN) AND daily close > weekly EMA13 AND daily impulse ≠ RED.

 

**Confluence rule:** require ≥ 2 of {A, B, C} entry triggers.

 

---

 

## 13. Extension / chase guardrail

 

| Metric | Severity points |

|---|---|

| 5-day % change ≥ 10% | +1 |

| 10-day % change ≥ 15% | +2 |

| Close > 10% above SMA20 | +1 |

| Close > 15% above SMA50 | +1 |

| Close > 5% above pattern pivot | +2 (and flag `chasing=true`) |

 

- If `chasing == true` → demote to `WATCH` regardless of score.
- If total severity ≥ 2 → reduce final score by **20**.

---

 

## 14. Market regime overlay (SPY)

 

- Pull SPY daily bars (one call per scan).
- Compute SPY EMA21.
- `regime_ok = SPY_close > EMA21 AND EMA21 rising over last 5 bars`.
- If `regime_ok == false`:
- Multiply every candidate's final score by **0.65**.
- Set top-level field `market_regime: "risk_off"`.

---

 

## 15. Final ranking score

 

For each surviving candidate:

 

```

final_score =

   0.40 × composite_score

 + 0.20 × (minervini_pass_count × 10)

 + 0.15 × (100 − rmv15)

 + 0.15 × rs_rank

 + 0.10 × elder_weekly_points

```

 

Where `elder_weekly_points`: `100` if weekly impulse GREEN, `50` if BLUE, `0` if RED.

 

Then apply: extension demote (§13) → regime multiplier (§14) → sort descending → concentration cap → portfolio risk cap → screening hook → exclude list → take top N where `final_score ≥ min_score`.

 

---

 

## 16. Entry, stop, target calculation

 

- **Entry zone:**
- Lower: pattern pivot + 0.1%
- Upper: `pivot × 1.02`
- **Stop floor (sanity-checked):** stop = `max( min(pattern_low, SMA50) × 0.999, entry_midpoint − 2 × ATR(14) )`
- The ATR floor prevents stops too close to entry when SMA50 sits just under price.
- **Guard:** if computed `stop ≥ entry_midpoint × 0.99`, reject the candidate with reason `INVALID_STOP_GEOMETRY`.
- **Risk per trade:** `(entry_midpoint − stop) / entry_midpoint` must be ≤ **7%**. If greater, reject with `RISK_TOO_WIDE`.
- **Target 1:** entry midpoint + `1.0 × base_height` (base_height = pattern high − pattern low)
- **Target 2:** entry midpoint + `1.5 × base_height`
- **Per-trade position size hint:** sized so entry-to-stop distance equals **1% of account capital risk**.
- **Portfolio cap:** sum of `position_size_hint_pct_account` across all returned candidates ≤ **12%**. Scale down proportionally if exceeded.

---

 

## 17. Output schema

 

```json

{

  "scan_id": "uuid",

  "as_of": "2026-06-27",

  "horizon_days": 30,

  "config_hash": "sha256:abc123...",

  "market_regime": "risk_on",

  "spy_close": 612.45,

  "spy_ema21": 598.10,

  "universe_size_after_liquidity": 487,

  "candidates_passing_all_gates": 23,

  "candidates_returned": 12,

  "api_calls_used": 612,

  "results": [

    {

      "symbol": "NVDA",

      "sector": "Technology",

      "signal": "BUY",

      "final_score": 84.2,

      "composite_score": 82,

      "stage": 2,

      "pattern": {

        "name": "VCP",

        "confirmed": true,

        "confidence": 0.78,

        "pivot": 168.50,

        "base_height": 12.30

      },

      "strategies_passing": ["minervini", "stine", "elder_weekly"],

      "minervini_pass_count": 8,

      "rs_rank": 91,

      "rmv15": 22,

      "rvol_today": 1.85,

      "atr_14": 3.45,

      "extension_severity": 0,

      "chasing": false,

      "entry_zone": [167.00, 171.87],

      "stop": 156.80,

      "risk_pct": 6.1,

      "target_1": 181.30,

      "target_2": 187.45,

      "position_size_hint_pct_account": 0.07,

      "thesis": "Stage 2 + tight VCP at pivot + Minervini 8/10 + Stine setup + Elder weekly GREEN"

    }

  ]

}

```

 

---

 

## 18. Caching, rate-limit, and resilience

 

- Cache daily bars per `(ticker, date)`. On rerun, fetch only delta since last cached date.
- Cache universe daily; refresh universe membership for backtest replays.
- Cap concurrent Massive requests at **5** (paid plans) or **1** (free tier).
- Respect 429 with exponential backoff: 1s, 2s, 4s, then fail.
- A full scan over ~500 liquid names should cost ~600 API calls; well within Massive Stocks Starter ($29/mo).
- Persist each scan's full result JSON plus a one-line summary (scan_id, as_of, count, regime, api_calls_used, config_hash).

---

 

## 19. Determinism & reproducibility

 

- Every scan must record `config_hash` (sha256 of the active config object) so the result can be replayed exactly.
- Re-running the same `(as_of, config_hash, universe_snapshot)` produces byte-identical scores.
- No call to wall-clock time inside any rule — all time references derive from `as_of` and the bar dates.

---

 

## 20. Acceptance criteria

 

- [ ] `POST /scan` returns within 60s on a 500-ticker universe with warm cache, 120s cold.
- [ ] `GET /scan/{id}` retrieves a prior scan unchanged.
- [ ] `GET /ticker/{symbol}` exposes every intermediate signal (each hard filter result, stage, every score component, each strategy trigger, extension flags) for debugging.
- [ ] Re-running the same `as_of` and same `config_hash` produces identical scores.
- [ ] **No-look-ahead test:** for each rule, the unit test verifies that altering any bar with `date > as_of` does not change the rule's output.
- [ ] All thresholds in this spec are loaded from a single config object.
- [ ] Each candidate's `thesis` lists the specific rules that triggered.
- [ ] `request_id` deduplication: same id within 60s returns the cached scan, not a new one.
- [ ] Sector concentration: no more than `max_per_sector` results from the same `sector`.
- [ ] Portfolio cap: sum of `position_size_hint_pct_account` ≤ 12%.

---

 

## 21. Calibration expectations (for the operator)

 

Set these as the baseline so you can tell "system is broken" apart from "system is just having a normal drawdown":

 

- Typical win rate on swing/breakout setups: **35–45%**.
- Typical reward-to-risk on winners reaching T1: **2:1** to **3:1**.
- Expected hit-rate of T1 within 30d on `BUY`-signaled candidates: **40–55%** in risk-on regimes; **20–30%** in risk-off.
- Expected median return per `BUY` over 30d: **+2% to +4%** before costs, in risk-on regimes.
- If observed win rate < 25% over a 30-trade sample in a risk-on regime → review composite weights, RS rank universe, and look-ahead audit.

---

 

## 22. Backtest mode (notes for downstream)

 

When `mode: "backtest"`:

- Universe must be reconstructed **as of the backtest date** (active tickers, sector mappings, liquidity ranks as of that date). Using today's universe injects survivorship bias.
- Bars must be unmodified by post-as_of corporate-action re-adjustments. Use point-in-time bar data if available.
- The same `config_hash` must produce identical results across reruns.

---

 

## 23. Optional post-rank screening hook

 

After ranking and before returning, the spec calls a single function:

 

```

screened = screening_filter(candidates, config) -> List[Candidate]

```

 

Default implementation = identity (no filtering). This is the clean seam for:

- Halal / Shariah compliance screening (e.g. Zoya, AAOIFI rules)
- ESG exclusions
- Internal compliance lists
- Any custom post-rank logic

Keep the seam in v1 even though the default is no-op — wiring it later costs zero refactoring.

 

---

 

## 24. What's deferred (v2 scope)

 

- Slippage / transaction-cost modeling in entry/stop math
- Trailing-stop and time-stop exit rules (this agent selects; it does not manage positions)
- Auto-tuned composite weights via backtest harness
- Walk-forward parameter validation

---

 

*Build spec v2 · Noor Technical Agent · Massive REST · 30-day bullish selector*

 
