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
- Frontend UI: `http://localhost:5173`

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

## 5) How To Use The App

- Open UI at `http://localhost:5173`.
- Select a timeframe (5m/15m/1h/1d).
- Signals:
- `TRIGGER_LONG`: RRS crosses up + RRV/RVE positive.
- `WATCH`: RRV/RVE positive, RRS rising but below zero.
- `NEUTRAL`: no clear signal.
- `EXIT/AVOID`: RRS crosses down or RRV/RVE negative.

Benchmark regime cards show trend/volatility/participation for NIFTY 50 and BANKNIFTY.

## 6) Troubleshooting

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

## 7) Development Workflow

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

Run backend against dockerized DB/Redis:

- Start `db` and `redis` with Docker compose.
- Run `uvicorn app.main:app --reload --port 8000` from `backend`.

Mock Groww locally:

- Swap the client in `app/infra/groww/client.py` with a stub, or mock at the service layer in tests.

## 8) Deployment Notes (Brief)

- Ensure all Groww credentials and DB/Redis URLs are set via environment variables.
- Place a reverse proxy (nginx/Caddy) in front of the backend if exposing publicly.
- Production cadence should be tuned to stay within Groww rate limits.

## 9) EC2 Runbook (Single Instance, Docker Compose)

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
