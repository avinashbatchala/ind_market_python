# Groww Scanner (India Market)

Production-grade trading scanner for NIFTY 50 and Bank universe. Backend is FastAPI + Postgres + Redis, frontend is Vue 3.

## 1) Prereqs

- Docker Engine 24+ and Docker Compose v2.
- Optional (non-Docker dev):
- Python 3.11+
- Node.js 20+

## 2) Quickstart (Docker)

1. Copy `.env.example` to `.env` and fill your Groww credentials.
2. Start the stack:

```bash
docker compose up --build
```

3. Verify services:

- Backend health: `http://localhost:8000/health`
- Frontend UI (via nginx): `http://localhost`

4. Logs:

```bash
docker compose logs -f backend
```

## 3) Database Setup

Migrations are Alembic-based. The backend container runs migrations automatically on startup.

Manual migration:

```bash
docker compose exec backend alembic upgrade head
```

Reset DB (drop volumes):

```bash
docker compose down -v
```

Inspect tables with psql:

```bash
docker compose exec db psql -U postgres -d groww_scanner
```

## 4) How The Scanner Works

Universes:

- NIFTY 50 list: `backend/app/domain/universe.py`
- Bank universe: `backend/app/domain/universe.py`

Time alignment:

- Candles are aligned by timestamp intersection. Missing candles are dropped (no forward fill).

Cadence:

- Ingestion interval: `SCHEDULER_INGEST_INTERVAL_SEC`
- Compute interval: `SCHEDULER_COMPUTE_INTERVAL_SEC`

Market hours:

- Default Asia/Kolkata 09:15-15:30, weekdays.
- Override with `MARKET_ALLOW_AFTER_HOURS=true` for testing.

Benchmark symbols:

- Ensure `NIFTY_SYMBOL=NIFTY` and `BANKNIFTY_SYMBOL=BANKNIFTY` (Groww trading symbols for the indices).
- Optional: `BENCHMARK_SYMBOLS` can add more index cards (comma-separated trading symbols).
- Watchlists and stock-to-index mapping are managed via the **Manage lists** page in the UI.

Signals + indicators:

- Source of truth is **this README** (sections 6–7). The markdown files in `docs/` are supplementary and may lag.

## 5) How To Use The App

- Open UI at `http://localhost:5173`.
- Select a timeframe (5m/15m/1h/1d).
- Use **Manage lists** to add stocks, indices, and map each stock to its industry index.
- Signals:
- `TRIGGER_LONG`: RRS crosses up + RRV/RVE positive.
- `TRIGGER_SHORT`: RRS crosses down + RRV/RVE negative.
- `WATCH`: RRV/RVE positive, RRS rising but below zero.
- `NEUTRAL`: no clear signal.
- `EXIT/AVOID`: RRS crosses down or RRV/RVE negative.

Benchmark regime cards show trend/volatility/participation for NIFTY 50 and BANKNIFTY.

## 6) Indicators, Scores, and Signal Math

This project uses **relative** measures, always comparing a stock to a benchmark (default: NIFTY).
All series are time‑aligned by timestamp intersection. Missing bars are dropped (no forward‑fill).
Warmup windows return `NaN` until enough data exists.

### 6.1 Core Notation

Let:

- `S` = stock, `B` = benchmark (NIFTY or sector index).
- `L` = lookback length (default 12).
- `close_t` = close at time `t`.
- `ΔS_t = close_S[t] - close_S[t-L]`.
- `ΔB_t = close_B[t] - close_B[t-L]`.

True Range and ATR (Wilder):

```
TR_t = max(
  high_t - low_t,
  abs(high_t - close_{t-1}),
  abs(low_t - close_{t-1})
)
ATR_t = WilderRMA(TR_t, L)
```

**Intuition:** ATR is a volatility‑scaled “step size”. It lets us compare moves across symbols with different prices.

### 6.2 Power‑surge protection (numerical stability)

All divisions are **stabilized** to avoid blow‑ups in quiet markets:

```
floor_t = rolling_quantile(den, q=0.05, window=252)
safe_div(num, den, floor) = num / max(den, floor)
power = clip(power, -pmax, +pmax)
```

- `rolling_floor` uses a long rolling quantile (5%) or fallback `median × frac`.
- `clip_power` clamps benchmark “power” to keep spikes from dominating.

**Intuition:** When the benchmark barely moves, the ratio `ΔB / ATR_B` can explode. Floors + clipping prevent that from dominating signal logic.

### 6.3 RRS — Relative Strength (price vs benchmark)

Formula:

```
power_t    = clip( safe_div(ΔB_t, ATR_B_t, floor_B), ±pmax )
expected_t = power_t * ATR_S_t
RRS_t      = safe_div(ΔS_t - expected_t, ATR_S_t, floor_S)
```

**Intuition:** If the benchmark moves by `power_t` ATR units, we expect the stock to move by the same *vol‑scaled* amount. RRS is how much the stock **outperformed** (positive) or **underperformed** (negative) that expectation.

### 6.4 RRV — Relative Volume‑momentum proxy

Volume is optionally log‑scaled:

```
v_t = log(max(volume_t, 1))  (default: true for NIFTY50)
v_t = SMA(v_t, smooth)       (optional smoothing)
```

Variance proxy (RMS by default):

```
dv_t   = v_t - v_{t-1}          (winsorized optional)
var_t  = sqrt( WilderRMA(dv_t^2, L) )
power  = clip( safe_div(ΔB_t, var_B_t, floor_B), ±pmax )
expected = power * var_S_t
RRV_t = safe_div(ΔS_t - expected, var_S_t, floor_S)
```

Winsorization (optional):

```
dv_t = clip(dv_t, q01, q99)
```

**Intuition:** RRV answers “Did price move more than expected given relative *volume variability*?”

### 6.5 RVE — Relative Volatility Expansion

ATR series is treated as its own “price”, then compared to benchmark:

```
ATR_S_t = WilderRMA(TR_S_t, atr_period)  (optional SMA smoothing)
ATR_B_t = WilderRMA(TR_B_t, atr_period)

dATR_t  = ATR_t - ATR_{t-1}              (winsorized optional)
var_t   = sqrt( WilderRMA(dATR_t^2, L) )
power   = clip( safe_div(ΔATR_B, var_B, floor_B), ±pmax )
expected = power * var_S
RVE_t   = safe_div(ΔATR_S - expected, var_S, floor_S)
```

**Intuition:** RVE measures whether the stock’s volatility is expanding faster (or slower) than the benchmark’s volatility expansion.

### 6.6 Optional Percent‑Units Mode (RRS/RVE)

When `use_pct_atr=True`:

```
move = log(close_t / close_{t-L})
ATR% = ATR / close
```

This keeps both move and ATR in **percentage space**, making comparisons more stable across price regimes.

### 6.7 Signal Definitions (Scanner)

Signals are derived from the indicators:

- `TRIGGER_LONG`: RRS crosses up + RRV/RVE positive.
- `TRIGGER_SHORT`: RRS crosses down + RRV/RVE negative.
- `WATCH`: RRV/RVE positive, RRS rising but below zero.
- `NEUTRAL`: no clear signal.
- `EXIT/AVOID`: RRS crosses down or RRV/RVE negative.

## 7) Intraday Options Decision Tree (Deterministic)

This is used to generate a **TradePlan** (no order placement).

### 7.1 Time Gate (IST)

- Reject trades before `09:25`.
- Reject trades after `14:45`.

### 7.2 Direction Gate

```
rrs_mkt  = RRS(stock vs NIFTY)
rrs_sec  = RRS(stock vs sector index)
rrs_sec_mkt = RRS(sector index vs NIFTY)
```

Rules:

- **BULL** if `rrs_mkt > 0.5` AND `rrs_sec > 0` AND `rrs_sec_mkt >= 0`
- **BEAR** if `rrs_mkt < -0.5` AND `rrs_sec < 0` AND `rrs_sec_mkt <= 0`
- Else: **NO TRADE**

### 7.3 Volatility Regime Gate

- `rve = RVE(stock vs NIFTY)`
- `iv_atm` = ATM IV from Groww option chain
- `iv_ref` = rolling median of ATM IV over last 60 minutes

Rules:

- **BUY_PREMIUM** if `rve > 0.3` and `iv_atm <= iv_ref`
- **SELL_PREMIUM** if `rve < -0.3` and `iv_atm >= iv_ref`
- Else: **NO TRADE**

### 7.4 Strategy Selection

- If **BULL**:
  - `BUY_PREMIUM` + `rrv > 0` → `BUY_CALL`
  - `SELL_PREMIUM` → `BULL_PUT_SPREAD`
  - Else → `BULL_CALL_SPREAD`
- If **BEAR**:
  - `BUY_PREMIUM` + `rrv < 0` → `BUY_PUT`
  - `SELL_PREMIUM` → `BEAR_CALL_SPREAD`
  - Else → `BEAR_PUT_SPREAD`

### 7.5 Expiry Selection

- Prefer the nearest weekly expiry with **>= 2 calendar days** to expiry.
- Fall back to next expiry if none match.

### 7.6 Contract Selection (Greeks + Liquidity)

Filters (configurable):

- `open_interest >= OI_min`
- `volume >= VOL_min`
- `ltp >= ltp_min`
- `spread_pct <= spread_max` (if bid/ask available)
- `abs(theta)/ltp <= theta_ratio_max`

Definitions:

```
theta_ratio = abs(theta) / ltp
spread_pct  = (ask - bid) / mid
mid         = (ask + bid) / 2
```

Delta bands:

- Long Call: `0.45–0.60`
- Long Put: `-0.60–-0.45`
- Credit short leg: `|delta| 0.15–0.30`

Scoring rewards (heuristic):

- Delta closeness to target
- Higher OI / volume
- Lower theta ratio / spread
- (for buys) lower IV relative to `iv_ref`

Example scoring:

```
score = -|delta - target|/span
        + 0.2*ln(1+OI) + 0.1*ln(1+Vol)
        - 1.5*theta_ratio - 0.5*spread_pct
        - iv_penalty
```

### 7.7 TradePlan Output (No Execution)

Each plan returns:

- Strategy type + legs (option contracts)
- `max_risk_pct`
- Entry type (limit preferred)
- Exits:
  - Indicator flip
  - Time stop (60–90 min)
  - Profit target and stop loss thresholds

## 8) Troubleshooting

Groww auth failures:

- Verify `GROWW_ACCESS_TOKEN` or API key/secret/TOTP values.
- Check the official SDK authentication flow for the latest requirements.

Rate limiting:

- The SDK enforces request limits. Defaults are set to `10 req/sec` and `300 req/min`.
- Reduce scan universes or increase cadence if throttling is observed.

Missing candles / misalignment:

- The scanner drops unmatched timestamps. Check for gaps in the source data.

Timezone issues:

- Ensure `MARKET_TZ=Asia/Kolkata` and that your system clock is correct.

Redis or Postgres issues:

- Verify container health and `DATABASE_URL` / `REDIS_URL` values.

## 9) Development Workflow

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Frontend dev server: `http://localhost:5173`

Run backend against dockerized DB/Redis:

- Start `db` and `redis` with Docker compose.
- Run `uvicorn app.main:app --reload --port 8000` from `backend`.

Mock Groww locally:

- Swap the client in `app/infra/groww/client.py` with a stub, or mock at the service layer in tests.

## 10) Deployment Notes (Brief)

- Ensure all Groww credentials and DB/Redis URLs are set via environment variables.
- Place a reverse proxy (nginx/Caddy) in front of the backend if exposing publicly.
- Production cadence should be tuned to stay within Groww rate limits.

## 11) EC2 Runbook (Single Instance, Docker Compose)

1. SSH into your EC2 instance.
2. Ensure Docker + Compose are installed.
3. Clone the repo into `/home/ubuntu/india_market_python`.
4. Export your Groww key for the session:

```bash
export GROWW_API_KEY="your-groww-key"
```

5. Run the deploy script (pulls `main`, builds with `--no-cache`, restarts):

```bash
cd /home/ubuntu/india_market_python
./deploy.sh
```

If you prefer not to export, pass the key directly:

```bash
./deploy.sh "your-groww-key"
```

## Architecture

- `backend/app/domain`: indicator math, alignment, universes
- `backend/app/infra`: Groww SDK wrapper, DB, cache
- `backend/app/services`: ingestion, compute, scheduler
- `backend/app/api`: REST + WebSocket

## Groww SDK References

- Authentication, instruments, historical candles, and feed endpoints live in the official Groww Python SDK docs.
- See:
- [Python SDK Introduction](https://groww.in/trade-api/docs/python-sdk/introduction)
- [Authentication](https://groww.in/trade-api/docs/python-sdk/authentication)
- [Historical Candles](https://groww.in/trade-api/docs/python-sdk/historical-data)
- [Feed / Streaming](https://groww.in/trade-api/docs/python-sdk/feed)
