# Indicators and Signal Interpretation

This project computes three relative metrics for each symbol against its **industry index**
(configured via the watchlist mapping) and uses them to derive signals. The main scanner
shows the benchmark index alongside each stock.

## Data Alignment

All calculations use aligned candles by timestamp intersection. If the symbol and
benchmark do not share at least 30 aligned candles, the symbol is skipped for that
timeframe.

## Metrics

All metrics are computed over a rolling window of 12 bars (`length=12`) unless
noted otherwise.

### RRS (Relative Strength)

RRS compares the symbol's price move to the benchmark's move, normalized by the
symbol's ATR:

- Compute each symbol's and benchmark's rolling close change over `length`.
- Convert the benchmark move into an "expected" symbol move by scaling with the
  symbol's ATR.
- RRS = (symbol move - expected move) / symbol ATR.

Interpretation:
- `RRS > 0` means the symbol is outperforming the benchmark on a volatility-adjusted basis.
- `RRS < 0` means underperformance.

### RRV (Relative Volume)

RRV measures whether the symbol's volume is expanding faster than expected vs the
benchmark:

- Volume is smoothed with a 3-bar SMA and log-transformed.
- Rolling change is compared to benchmark change, normalized by volume variability.

Interpretation:
- `RRV > 0` means relative volume expansion.
- `RRV < 0` means relative volume contraction.

### RVE (Relative Volatility Expansion)

RVE measures whether the symbol's volatility (ATR) is expanding faster than expected
vs the benchmark:

- ATR uses a 14-bar Wilder RMA.
- The ATR series is optionally smoothed (currently `smooth_atr=1`, so no extra smoothing).
- Rolling change is compared to benchmark change, normalized by ATR variability.

Interpretation:
- `RVE > 0` means relative volatility expansion.
- `RVE < 0` means contraction.

## Signals

Signals are derived from the latest RRS/RRV/RVE values and recent RRS movement:

- `TRIGGER_LONG`: RRS crosses up through 0 **and** RRV > 0 **and** RVE > 0.
- `TRIGGER_SHORT`: RRS crosses down through 0 **and** RRV < 0 **and** RVE < 0.
- `WATCH`: RRV > 0 and RVE > 0, RRS < 0 but rising (latest > previous).
- `EXIT/AVOID`: RRS crosses down through 0 **or** RRV < 0 **or** RVE < 0.
- `NEUTRAL`: none of the above.

## Filters

The UI provides min/max range filters for **RRS**, **RRV**, and **RVE** so you can
screen for both bullish and bearish relative setups without using a composite score.
You can manage stocks, indices, and their mappings on the **Manage lists** page.

## Ranking

Rows are ranked by:

1. Signal priority (`TRIGGER_LONG`, `TRIGGER_SHORT`, `WATCH`, `NEUTRAL`, `EXIT/AVOID`)
2. Higher absolute `RRS` (stronger relative move)
3. Higher absolute `RVE` (stronger volatility expansion/contraction)

## Notes

These metrics are intended for relative screening, not standalone trade decisions.
Always validate with your own risk and execution rules.
