"""Error analysis for March 1, 2026 backtest."""
import asyncio
import json
import httpx

API = 'http://localhost:8000/api/v1/backtest/single'
TICKERS = ['AAPL','MSFT','NVDA','GOOGL','TSLA','AVGO','LLY','JNJ','UNH','PFE',
    'ABBV','TMO','ABT','DHR','MRK','HD','COST','TGT','NKE','PG','KO','PEP','WMT',
    'ORCL','ADBE','CRM','CSCO','AMD','QCOM','TXN','AMAT','BA','CAT','DE','UPS',
    'HON','XOM','CVX','COP','LIN','APD','V','MA','PYPL','DDOG','CRWD','PANW','NOW','TSM','IBM']

async def main():
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(API, json={
            'as_of_date': '2026-03-01', 'tickers': TICKERS, 'horizon_days': 30
        })
        data = resp.json()

    trades = data.get('trades', [])
    print(f"Date: {data['as_of_date']} | Market: {data['market_regime']}")
    print(f"Avg Return: {data['metrics']['avg_return']:.1f}%")
    print(f"Trades: {len(trades)}")
    print()

    tp = [t for t in trades if t['score'] >= 50 and t['max_gain_pct'] >= 5]
    fp = [t for t in trades if t['score'] >= 50 and t['max_gain_pct'] < 5]
    fn = [t for t in trades if t['score'] < 50 and t['max_gain_pct'] >= 5]
    tn = [t for t in trades if t['score'] < 50 and t['max_gain_pct'] < 5]

    print(f"TP={len(tp)} FP={len(fp)} FN={len(fn)} TN={len(tn)}")
    print()

    print(f"=== FALSE POSITIVES ({len(fp)}) - Scored >=50 but DIDNT gain 5% ===")
    for t in sorted(fp, key=lambda x: -x['score']):
        s = t.get('signals', {})
        print(f"  {t['ticker']:<5} score={t['score']:>2} | entry=${t['entry_price']:.0f} "
              f"max_gain={t['max_gain_pct']:+.1f}% return={t['return_pct']:+.1f}%")
        print(f"         SMA50={s.get('price_above_sma50')} EMA20={s.get('price_above_ema20')} "
              f"MACD={s.get('macd_above_signal')} Vol={s.get('volume_above_average')} "
              f"RS={s.get('relative_strength_positive')}")

    print()
    print(f"=== FALSE NEGATIVES ({len(fn)}) - Gained 5%+ but scored <50 ===")
    for t in sorted(fn, key=lambda x: -x['max_gain_pct']):
        s = t.get('signals', {})
        print(f"  {t['ticker']:<5} score={t['score']:>2} | entry=${t['entry_price']:.0f} "
              f"max_gain={t['max_gain_pct']:+.1f}% return={t['return_pct']:+.1f}%")
        print(f"         SMA50={s.get('price_above_sma50')} EMA20={s.get('price_above_ema20')} "
              f"MACD={s.get('macd_above_signal')} Vol={s.get('volume_above_average')} "
              f"RS={s.get('relative_strength_positive')}")

    print()
    print(f"=== TRUE POSITIVES ({len(tp)}) ===")
    for t in sorted(tp, key=lambda x: -x['score']):
        print(f"  {t['ticker']:<5} score={t['score']:>2} | max_gain={t['max_gain_pct']:+.1f}% "
              f"return={t['return_pct']:+.1f}%")

    print()
    scores = [t['score'] for t in trades]
    gains = [t['max_gain_pct'] for t in trades]
    print(f"=== DISTRIBUTION ===")
    print(f"  Scores: min={min(scores)} max={max(scores)} mean={sum(scores)/len(scores):.0f}")
    print(f"  Gains:  min={min(gains):.1f}% max={max(gains):.1f}% mean={sum(gains)/len(gains):.1f}%")
    print(f"  Gained >=5%: {len([g for g in gains if g>=5])}/{len(gains)}")
    print(f"  Scored >=50: {len([s for s in scores if s>=50])}/{len(scores)}")
    
    # Key pattern: what do FP stocks have in common?
    print()
    print("=== PATTERN ANALYSIS ===")
    fp_signals = {'sma50': 0, 'ema20': 0, 'macd': 0, 'vol': 0, 'rs': 0}
    for t in fp:
        s = t.get('signals', {})
        if s.get('price_above_sma50'): fp_signals['sma50'] += 1
        if s.get('price_above_ema20'): fp_signals['ema20'] += 1
        if s.get('macd_above_signal'): fp_signals['macd'] += 1
        if s.get('volume_above_average'): fp_signals['vol'] += 1
        if s.get('relative_strength_positive'): fp_signals['rs'] += 1
    print(f"  FP signal frequency ({len(fp)} stocks):")
    for k, v in fp_signals.items():
        print(f"    {k}: {v}/{len(fp)} ({v*100//max(len(fp),1)}%)")

    fn_signals = {'sma50': 0, 'ema20': 0, 'macd': 0, 'vol': 0, 'rs': 0}
    for t in fn:
        s = t.get('signals', {})
        if s.get('price_above_sma50'): fn_signals['sma50'] += 1
        if s.get('price_above_ema20'): fn_signals['ema20'] += 1
        if s.get('macd_above_signal'): fn_signals['macd'] += 1
        if s.get('volume_above_average'): fn_signals['vol'] += 1
        if s.get('relative_strength_positive'): fn_signals['rs'] += 1
    print(f"  FN signal frequency ({len(fn)} stocks):")
    for k, v in fn_signals.items():
        print(f"    {k}: {v}/{len(fn)} ({v*100//max(len(fn),1)}%)")

asyncio.run(main())
