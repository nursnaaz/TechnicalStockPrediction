"""
Comprehensive Backtest Report Generator

Runs backtests across 5 different dates with 50 tickers each,
calculates confusion matrix, portfolio returns, and generates
an HTML report.
"""
import asyncio
import json
from datetime import datetime
import httpx

API = 'http://localhost:8000/api/v1/backtest/single'

# 50 diverse halal tickers (tech, healthcare, consumer, energy, fintech)
TICKERS = [
    'AAPL','MSFT','NVDA','GOOGL','GOOG','TSLA','AVGO','LLY','JNJ','UNH',
    'PFE','ABBV','TMO','ABT','DHR','MRK','BMY','AMGN','GILD','REGN',
    'VRTX','ISRG','HD','COST','TGT','NKE','SBUX','MCD','CMG','LULU',
    'PG','KO','PEP','WMT','ORCL','ADBE','CRM','CSCO','INTC','AMD',
    'QCOM','TXN','AMAT','LRCX','KLAC','MRVL','BA','CAT','DE','UPS',
    'HON','GE','LMT','RTX','XOM','CVX','COP','SLB','EOG','LIN',
    'APD','SHW','T','VZ','TMUS','V','MA','PYPL','FIS','FISV',
    'SHOP','UBER','DDOG','CRWD','ZS','PANW','NET','MDB','SNOW','NOW',
    'TEAM','ZM','TSM','IBM','CL','KMB','HSY','MDLZ','CLX','BKNG',
    'PLD','AMT','EQIX','PSA','DLR','BBY','SNPS','CDNS','NXPI','ADI',
    'AMZN','META','RIVN','F','GM','ENPH','FSLR','PLUG',
]

# 5 different dates across different market conditions
DATES = [
    ('2024-04-15', 'Spring 2024 - Tech correction'),
    ('2024-08-01', 'Summer 2024 - Pre-election'),
    ('2024-11-15', 'Nov 2024 - Post-election rally'),
    ('2025-02-01', 'Feb 2025 - Market peak'),
    ('2025-05-01', 'May 2025 - Recovery'),
]

SCORE_THRESHOLD = 50
GAIN_THRESHOLD = 5


async def run_backtest(date, tickers):
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(API, json={
            'as_of_date': date, 'tickers': tickers, 'horizon_days': 30
        })
        return resp.json()

async def main():
    all_results = []
    all_trades = []

    print("Running backtests across 5 dates with 50 tickers each...")
    for date, desc in DATES:
        print(f"  {date} ({desc})...")
        data = await run_backtest(date, TICKERS)
        trades = [t for t in data.get('trades', []) if t.get('status') == 'analyzed']
        all_results.append({'date': date, 'desc': desc, 'data': data, 'trades': trades})
        all_trades.extend([{**t, 'date': date} for t in trades])

    print(f"\nTotal trades analyzed: {len(all_trades)}")

    # === CALCULATE METRICS ===
    # Per-date metrics
    date_metrics = []
    for r in all_results:
        trades = r['trades']
        tp = len([t for t in trades if t['score'] >= SCORE_THRESHOLD and t['max_gain_pct'] >= GAIN_THRESHOLD])
        fp = len([t for t in trades if t['score'] >= SCORE_THRESHOLD and t['max_gain_pct'] < GAIN_THRESHOLD])
        fn = len([t for t in trades if t['score'] < SCORE_THRESHOLD and t['max_gain_pct'] >= GAIN_THRESHOLD])
        tn = len([t for t in trades if t['score'] < SCORE_THRESHOLD and t['max_gain_pct'] < GAIN_THRESHOLD])
        total = tp + fp + fn + tn
        prec = tp/(tp+fp) if (tp+fp) > 0 else 0
        rec = tp/(tp+fn) if (tp+fn) > 0 else 0
        f1 = 2*prec*rec/(prec+rec) if (prec+rec) > 0 else 0

        # Portfolio return: if we invest equal $ in all predicted-bullish stocks
        predicted_bullish = [t for t in trades if t['score'] >= SCORE_THRESHOLD]
        if predicted_bullish:
            avg_return_predicted = sum(t['return_pct'] for t in predicted_bullish) / len(predicted_bullish)
        else:
            avg_return_predicted = 0

        # Buy-and-hold all stocks (baseline)
        avg_return_all = sum(t['return_pct'] for t in trades) / len(trades) if trades else 0

        date_metrics.append({
            'date': r['date'], 'desc': r['desc'], 'regime': r['data'].get('market_regime', '?'),
            'total': total, 'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
            'precision': prec, 'recall': rec, 'f1': f1,
            'predicted_count': len(predicted_bullish),
            'portfolio_return': avg_return_predicted,
            'baseline_return': avg_return_all,
            'alpha': avg_return_predicted - avg_return_all,
        })

    # Overall metrics
    tp_all = sum(d['tp'] for d in date_metrics)
    fp_all = sum(d['fp'] for d in date_metrics)
    fn_all = sum(d['fn'] for d in date_metrics)
    tn_all = sum(d['tn'] for d in date_metrics)
    total_all = tp_all + fp_all + fn_all + tn_all
    prec_all = tp_all/(tp_all+fp_all) if (tp_all+fp_all) > 0 else 0
    rec_all = tp_all/(tp_all+fn_all) if (tp_all+fn_all) > 0 else 0
    f1_all = 2*prec_all*rec_all/(prec_all+rec_all) if (prec_all+rec_all) > 0 else 0
    acc_all = (tp_all+tn_all)/total_all if total_all > 0 else 0

    # Portfolio simulation: $10,000 per predicted stock per period
    total_invested = 0
    total_return_dollars = 0
    for d in date_metrics:
        if d['predicted_count'] > 0:
            invested = 10000 * d['predicted_count']
            returned = invested * (1 + d['portfolio_return']/100)
            total_invested += invested
            total_return_dollars += (returned - invested)

    portfolio_pct = (total_return_dollars / total_invested * 100) if total_invested > 0 else 0

    # === PRINT CONSOLE SUMMARY ===
    print("\n" + "=" * 80)
    print("COMPREHENSIVE BACKTEST REPORT")
    print(f"Engine: V2 + Stage 2 + Pattern Detection + Recovery Bonus")
    print(f"Thresholds: Score ≥{SCORE_THRESHOLD}, Gain ≥{GAIN_THRESHOLD}%, Horizon 30 days")
    print(f"Universe: {len(TICKERS)} tickers, {len(DATES)} dates")
    print("=" * 80)

    print(f"\n{'Date':<12} {'Regime':<8} {'TP':>3} {'FP':>3} {'FN':>3} {'TN':>3} | {'Prec':>5} {'Rec':>5} {'F1':>5} | {'Port%':>6} {'Base%':>6} {'Alpha':>6}")
    print("-" * 90)
    for d in date_metrics:
        print(f"{d['date']:<12} {d['regime']:<8} {d['tp']:>3} {d['fp']:>3} {d['fn']:>3} {d['tn']:>3} | {d['precision']*100:>4.0f}% {d['recall']*100:>4.0f}% {d['f1']*100:>4.0f}% | {d['portfolio_return']:>+5.1f}% {d['baseline_return']:>+5.1f}% {d['alpha']:>+5.1f}%")

    print("-" * 90)
    print(f"{'OVERALL':<12} {'':8} {tp_all:>3} {fp_all:>3} {fn_all:>3} {tn_all:>3} | {prec_all*100:>4.0f}% {rec_all*100:>4.0f}% {f1_all*100:>4.0f}% | {portfolio_pct:>+5.1f}%")

    print(f"\n--- PORTFOLIO SIMULATION ---")
    print(f"Strategy: Invest $10,000 in each stock scored ≥{SCORE_THRESHOLD} at each date")
    print(f"Total invested: ${total_invested:,.0f}")
    print(f"Total P&L: ${total_return_dollars:>+,.0f}")
    print(f"Portfolio return: {portfolio_pct:>+.1f}%")

    # === GENERATE HTML REPORT ===
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Backtest Report - {datetime.now().strftime('%Y-%m-%d')}</title>
<style>
body{{font-family:system-ui,-apple-system,sans-serif;max-width:1200px;margin:0 auto;padding:24px;background:#f8fafc;color:#1a202c}}
h1{{color:#0972d3;border-bottom:2px solid #0972d3;padding-bottom:8px}}
h2{{color:#2d3748;margin-top:32px}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:20px 0}}
.card{{background:white;border-radius:8px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.1);text-align:center}}
.card .value{{font-size:2.2em;font-weight:bold;color:#0972d3}}
.card .label{{color:#718096;font-size:0.85em;margin-top:4px}}
.card.good .value{{color:#38a169}}
.card.bad .value{{color:#e53e3e}}
table{{border-collapse:collapse;width:100%;margin:16px 0;background:white;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1)}}
th{{background:#2d3748;color:white;padding:12px 8px;text-align:left;font-size:0.85em}}
td{{padding:10px 8px;border-bottom:1px solid #e2e8f0;font-size:0.9em}}
tr:hover{{background:#f7fafc}}
.tp{{background:#f0fff4}}.fp{{background:#fff5f5}}.fn{{background:#fffff0}}.tn{{background:#f7fafc}}
.positive{{color:#38a169;font-weight:bold}}.negative{{color:#e53e3e;font-weight:bold}}
.cm-grid{{display:grid;grid-template-columns:140px 1fr 1fr;gap:4px;max-width:450px;margin:16px 0}}
.cm-cell{{text-align:center;padding:20px;border-radius:6px;font-size:1.4em;font-weight:bold}}
.cm-header{{padding:10px;font-weight:bold;background:#edf2f7;text-align:center;border-radius:4px}}
.cm-label{{font-size:0.45em;display:block;margin-top:4px;font-weight:normal}}
.summary{{background:#ebf8ff;border:1px solid #bee3f8;border-radius:8px;padding:16px;margin:16px 0}}
</style></head><body>
<h1>Bullish Stock Scanner - Backtest Report</h1>
<div class="summary">
<strong>Configuration:</strong> Score ≥{SCORE_THRESHOLD} | Gain ≥{GAIN_THRESHOLD}% | Horizon: 30 days | 
{len(TICKERS)} tickers | {len(DATES)} test periods | Engine: V2 + Stage 2 + Patterns + Recovery
</div>

<h2>Overall Performance</h2>
<div class="grid">
<div class="card {'good' if acc_all >= 0.5 else 'bad'}"><div class="value">{acc_all*100:.0f}%</div><div class="label">Accuracy<br>(TP+TN)/Total</div></div>
<div class="card {'good' if prec_all >= 0.6 else 'bad'}"><div class="value">{prec_all*100:.0f}%</div><div class="label">Precision<br>When we say bullish, how often right</div></div>
<div class="card {'good' if rec_all >= 0.5 else 'bad'}"><div class="value">{rec_all*100:.0f}%</div><div class="label">Recall<br>Of all gainers, how many we caught</div></div>
<div class="card"><div class="value">{f1_all*100:.0f}%</div><div class="label">F1 Score<br>Balance of precision & recall</div></div>
</div>

<h2>Confusion Matrix (All Periods Combined)</h2>
<div class="cm-grid">
<div></div><div class="cm-header">Actually ≥{GAIN_THRESHOLD}%</div><div class="cm-header">Actually &lt;{GAIN_THRESHOLD}%</div>
<div class="cm-header">Predicted ≥{SCORE_THRESHOLD}</div>
<div class="cm-cell" style="background:#c6f6d5">{tp_all}<span class="cm-label">TRUE POSITIVE</span></div>
<div class="cm-cell" style="background:#fed7d7">{fp_all}<span class="cm-label">FALSE POSITIVE</span></div>
<div class="cm-header">Predicted &lt;{SCORE_THRESHOLD}</div>
<div class="cm-cell" style="background:#fefcbf">{fn_all}<span class="cm-label">FALSE NEGATIVE</span></div>
<div class="cm-cell" style="background:#e2e8f0">{tn_all}<span class="cm-label">TRUE NEGATIVE</span></div>
</div>

<h2>Portfolio Simulation</h2>
<div class="grid">
<div class="card"><div class="value">${total_invested:,.0f}</div><div class="label">Total Invested</div></div>
<div class="card {'good' if total_return_dollars > 0 else 'bad'}"><div class="value">${total_return_dollars:>+,.0f}</div><div class="label">Total P&L</div></div>
<div class="card {'good' if portfolio_pct > 0 else 'bad'}"><div class="value">{portfolio_pct:>+.1f}%</div><div class="label">Portfolio Return</div></div>
<div class="card"><div class="value">{sum(d['predicted_count'] for d in date_metrics)}</div><div class="label">Total Trades Taken</div></div>
</div>
<p><em>Strategy: Invest $10,000 in each stock predicted bullish (score ≥{SCORE_THRESHOLD}). Hold for 30 days.</em></p>

<h2>Performance by Date</h2>
<table>
<tr><th>Date</th><th>Market</th><th>Trades</th><th>TP</th><th>FP</th><th>FN</th><th>TN</th><th>Precision</th><th>Recall</th><th>F1</th><th>Portfolio</th><th>Baseline</th><th>Alpha</th></tr>
"""
    for d in date_metrics:
        alpha_class = 'positive' if d['alpha'] > 0 else 'negative'
        html += f"""<tr><td>{d['date']}</td><td>{d['regime']}</td><td>{d['total']}</td>
<td>{d['tp']}</td><td>{d['fp']}</td><td>{d['fn']}</td><td>{d['tn']}</td>
<td>{d['precision']*100:.0f}%</td><td>{d['recall']*100:.0f}%</td><td>{d['f1']*100:.0f}%</td>
<td class="{'positive' if d['portfolio_return']>0 else 'negative'}">{d['portfolio_return']:+.1f}%</td>
<td>{d['baseline_return']:+.1f}%</td>
<td class="{alpha_class}">{d['alpha']:+.1f}%</td></tr>"""

    html += """</table>
<p><strong>Alpha</strong> = Portfolio return minus baseline (buy-all) return. Positive alpha means our predictions outperformed random stock selection.</p>

<h2>All Trades</h2>
<table><tr><th>Date</th><th>Ticker</th><th>Score</th><th>Entry</th><th>Max Price</th><th>Max Gain</th><th>30d Return</th><th>Classification</th></tr>
"""
    for t in sorted(all_trades, key=lambda x: (-x.get('score', 0))):
        predicted = t['score'] >= SCORE_THRESHOLD
        actual = t['max_gain_pct'] >= GAIN_THRESHOLD
        if predicted and actual: cls, cls_name = 'tp', 'TP'
        elif predicted and not actual: cls, cls_name = 'fp', 'FP'
        elif not predicted and actual: cls, cls_name = 'fn', 'FN'
        else: cls, cls_name = 'tn', 'TN'
        html += f"""<tr class="{cls}"><td>{t['date']}</td><td><strong>{t['ticker']}</strong></td><td>{t['score']}</td>
<td>${t['entry_price']:.2f}</td><td>${t.get('max_price',0):.2f}</td>
<td class="{'positive' if t['max_gain_pct']>=GAIN_THRESHOLD else ''}">{t['max_gain_pct']:.1f}%</td>
<td class="{'positive' if t['return_pct']>0 else 'negative'}">{t['return_pct']:.1f}%</td>
<td>{cls_name}</td></tr>"""

    html += f"""</table>
<hr><p><em>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Engine: V2 + Stage 2 + Pattern Detection + Recovery</em></p>
</body></html>"""

    # Save report
    report_path = '/Users/mohamednoordeenalaudeen/Documents/GenAI-2026/Agentic Coding/TechnicalStockPrediction/backtest_report.html'
    with open(report_path, 'w') as f:
        f.write(html)
    print(f"\nHTML report saved to: {report_path}")


asyncio.run(main())
