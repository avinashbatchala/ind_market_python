# RRS / RRV / RVE Stability Notes

This repo uses RRS/RRV/RVE indicators from `backend/app/domain/indicators/rrs_rrv_rve.py`.

## Numerical Stability

- **safe_div**: protects divisions with a rolling denominator floor.
- **rolling_floor**: uses a rolling quantile (default 5%) or rolling median fallback.
- **clip_power**: clamps benchmark power to `[-pmax, +pmax]` (default 10) to avoid blow-ups.

## Variance Proxy (RRV/RVE)

- Default `var_mode="rms"` uses `sqrt(RMA(diff^2))`.
- Legacy `var_mode="abs"` uses `RMA(abs(diff))`.
- Optional winsorization caps diff outliers (default 1% / 99%).

## Percent-ATR Normalization (Optional)

RRS/RVE support `use_pct_atr=True` to normalize by ATR% and log-returns for moves.
Default is `False` to preserve historical behavior.

## Recommended Defaults (NIFTY50 daily)

- `length=20..30`
- `atr_period=14`
- `power_clip=10`
- `log_volume=True`
- `var_mode="rms"`
