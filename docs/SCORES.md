# Score Calculation and Interpretation

This project computes three relative metrics for each symbol against two benchmarks
(`NIFTY` and `BANKNIFTY`) and derives a simple score and signal.

## Data Alignment

All calculations use aligned candles by timestamp intersection. If the symbol and
benchmark do not share at least 30 aligned candles, the symbol is skipped for that
timeframe.

## Metrics

All metrics are computed over a rolling window of 12 bars (`length=12`) unless
noted otherwise.

### RRS (Relative Strength)

RRS compares the symbol's price move to the benchmark's price move, normalized by
the symbol's ATR:

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

## Score

Score is a simple 0–3 count of positive components:

```
score = (RRS > 0) + (RRV > 0) + (RVE > 0)
```

## Signals

Signals are derived from the latest RRS/RRV/RVE values and recent RRS movement:

- `TRIGGER_LONG`: RRS crosses up through 0 **and** RRV > 0 **and** RVE > 0.
- `WATCH`: RRV > 0 and RVE > 0, RRS < 0 but rising (latest > previous).
- `EXIT/AVOID`: RRS crosses down through 0 **or** RRV < 0 **or** RVE < 0.
- `NEUTRAL`: none of the above.

Each symbol is scored against **both** benchmarks:

- `*_vs_nifty` (NIFTY)
- `*_vs_bank` (BANKNIFTY)

The UI surfaces a `best_signal`, which chooses the better of the two signals using
priority:

```
TRIGGER_LONG > WATCH > NEUTRAL > EXIT/AVOID
```

## Ranking

Rows are ranked by:

1. `best_signal` priority
2. Higher of `score_vs_nifty` and `score_vs_bank`
3. Higher of `rve_vs_nifty` and `rve_vs_bank`

## Notes

These metrics are intended for relative screening, not standalone trade decisions.
Always validate with your own risk and execution rules.
