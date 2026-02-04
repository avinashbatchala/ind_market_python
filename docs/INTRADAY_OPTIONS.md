# Intraday Options Strategy (NIFTY50)

## Decision Tree (Text)

1. **Time Gate**
   - Reject before 09:25 and after 14:45 (configurable).
2. **Direction Gate**
   - Compute: RRS(sym vs NIFTY), RRS(sym vs sector), RRS(sector vs NIFTY)
   - BULL if rrs_mkt > 0.5 and rrs_sec > 0 and rrs_sector_vs_mkt >= 0
   - BEAR if rrs_mkt < -0.5 and rrs_sec < 0 and rrs_sector_vs_mkt <= 0
3. **Volatility Regime Gate**
   - Compute RVE(sym vs NIFTY)
   - Get ATM IV from option chain
   - Rolling IV reference = median of last 30–60 min
   - BUY_PREMIUM if rve > 0.3 and iv_atm <= iv_ref
   - SELL_PREMIUM if rve < -0.3 and iv_atm >= iv_ref
4. **Strategy Selection**
   - BULL + BUY_PREMIUM + rrv > 0 → BUY_CALL
   - BULL + SELL_PREMIUM → BULL_PUT_SPREAD
   - BEAR + BUY_PREMIUM + rrv < 0 → BUY_PUT
   - BEAR + SELL_PREMIUM → BEAR_CALL_SPREAD

## Contract Selection

- Liquidity filters: OI, volume, spread, min premium
- Delta bands: long ~0.52, short ~0.20
- Theta ratio sanity filter
- Scoring: delta closeness + liquidity, penalize spreads and theta

## Defaults

See `backend/app/config/strategy.py` for configurable thresholds and risk settings.

## Running

Example usage (inside code):

```
engine = IntradayOptionsEngine(
    settings,
    candle_repo,
    ticker_index_repo,
    watch_index_repo,
    cache,
    live_data,
    iv_tracker,
)
plans = engine.generate_trade_plans(now, symbols)
```

## IV Tracking

`IvTracker` stores ATM IV snapshots per symbol and returns a rolling median (default 60 min window).
