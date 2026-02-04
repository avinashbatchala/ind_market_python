from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Dict, List, Optional

from app.config.strategy import IntradayStrategyConfig
from app.core.config import Settings
from app.domain.alignment import align_ohlcv
from app.domain.indicators.rrs_rrv_rve import rrs, rrv, rve
from app.domain.options.groww_chain_adapter import normalize_chain, compute_atm_iv
from app.domain.options.iv_tracker import IvTracker
from app.domain.strategy.contract_selector import (
    select_long_call,
    select_long_put,
    select_credit_spread,
    select_debit_spread,
)
from app.domain.strategy.models import Direction, Regime, StrategyType, TradePlan, EntryType, OptionLeg, OptionType
from app.infra.cache.redis_cache import RedisCache
from app.infra.db.repositories import CandleRepository, TickerIndexRepository, WatchIndexRepository
from app.services.candles_repo import CandlesRepo
from app.services.groww_live_data import GrowwLiveDataService


@dataclass
class IndicatorSet:
    rrs_mkt: float
    rrs_sec: float
    rrs_sector_vs_mkt: float
    rrv: float
    rve: float


class IntradayOptionsEngine:
    def __init__(
        self,
        settings: Settings,
        candle_repo: CandleRepository,
        ticker_index_repo: TickerIndexRepository,
        watch_index_repo: WatchIndexRepository,
        cache: RedisCache,
        live_data: GrowwLiveDataService,
        iv_tracker: IvTracker,
        config: IntradayStrategyConfig | None = None,
    ) -> None:
        self.settings = settings
        self.candle_repo = candle_repo
        self.ticker_index_repo = ticker_index_repo
        self.watch_index_repo = watch_index_repo
        self.cache = cache
        self.candles_repo = CandlesRepo(candle_repo, cache)
        self.live_data = live_data
        self.iv_tracker = iv_tracker
        self.config = config or IntradayStrategyConfig()

    def generate_trade_plans(self, now: datetime, symbols: List[str]) -> List[TradePlan]:
        if not self._within_gate(now):
            return []

        plans: List[TradePlan] = []
        for symbol in symbols:
            indicator_set = self._compute_indicators(symbol)
            if indicator_set is None:
                continue

            direction = self._direction_gate(indicator_set)
            if direction == Direction.NONE:
                continue

            chain_raw, expiry_date = self._fetch_chain(symbol)
            if chain_raw is None or expiry_date is None:
                continue

            contracts, underlying_price = normalize_chain(chain_raw, symbol)
            if not contracts:
                continue

            iv_atm = compute_atm_iv(contracts, underlying_price)
            if iv_atm is None:
                continue

            self.iv_tracker.update(symbol, now, iv_atm)
            iv_ref = self.iv_tracker.get_ref(symbol, now)
            if iv_ref is None:
                continue

            regime = self._vol_regime(indicator_set.rve, iv_atm, iv_ref)
            if regime == Regime.NONE:
                continue

            strategy = self._select_strategy(direction, regime, indicator_set.rrv)
            if strategy == StrategyType.NONE:
                continue

            legs = self._select_contracts(strategy, contracts, iv_ref)
            if not legs:
                continue

            dte = _days_to_expiry(expiry_date, now)
            plan = TradePlan(
                symbol=symbol,
                direction=direction,
                regime=regime,
                strategy=strategy,
                legs=legs,
                dte=dte,
                max_risk_pct=self.config.max_risk_pct,
                entry_type=EntryType.LIMIT,
                exits=self._exit_rules(strategy),
                timestamp=now.isoformat(),
                notes=[f"iv_atm={iv_atm:.2f}", f"iv_ref={iv_ref:.2f}"]
            )
            plans.append(plan)
        return plans

    def _within_gate(self, now: datetime) -> bool:
        tz = self.settings.market_tz
        local = now.astimezone(_tzinfo(tz))
        start = _parse_time(self.config.gate_start)
        end = _parse_time(self.config.gate_end)
        return start <= local.time() <= end

    def _compute_indicators(self, symbol: str) -> Optional[IndicatorSet]:
        symbol = symbol.upper()
        sector = self._sector_index(symbol)
        market = self.settings.nifty_symbol

        data_symbols = {symbol, sector, market}
        mapping = self.watch_index_repo.get_active_mappings()
        mapped = {s: mapping.get(s, s) for s in data_symbols}

        candles = self.candles_repo.get_candles(sorted(mapped.values()), self.config.timeframe, self.config.lookback)
        sym_data = candles.get(mapped[symbol])
        sec_data = candles.get(mapped[sector])
        mkt_data = candles.get(mapped[market])
        if sym_data is None or sec_data is None or mkt_data is None:
            return None

        rrs_mkt = _compute_rrs(sym_data, mkt_data)
        rrs_sec = _compute_rrs(sym_data, sec_data)
        rrs_sector_vs_mkt = _compute_rrs(sec_data, mkt_data)
        rrv_val = _compute_rrv(sym_data, mkt_data)
        rve_val = _compute_rve(sym_data, mkt_data)

        if None in (rrs_mkt, rrs_sec, rrs_sector_vs_mkt, rrv_val, rve_val):
            return None

        return IndicatorSet(
            rrs_mkt=rrs_mkt,
            rrs_sec=rrs_sec,
            rrs_sector_vs_mkt=rrs_sector_vs_mkt,
            rrv=rrv_val,
            rve=rve_val,
        )

    def _direction_gate(self, ind: IndicatorSet) -> Direction:
        if ind.rrs_mkt > self.config.rrs_market_threshold and ind.rrs_sec > self.config.rrs_sector_threshold and ind.rrs_sector_vs_mkt >= 0:
            return Direction.BULL
        if ind.rrs_mkt < -self.config.rrs_market_threshold and ind.rrs_sec < -self.config.rrs_sector_threshold and ind.rrs_sector_vs_mkt <= 0:
            return Direction.BEAR
        return Direction.NONE

    def _vol_regime(self, rve_val: float, iv_atm: float, iv_ref: float) -> Regime:
        if rve_val > self.config.rve_buy_threshold and iv_atm <= iv_ref:
            return Regime.BUY_PREMIUM
        if rve_val < self.config.rve_sell_threshold and iv_atm >= iv_ref:
            return Regime.SELL_PREMIUM
        return Regime.NONE

    def _select_strategy(self, direction: Direction, regime: Regime, rrv_val: float) -> StrategyType:
        if direction == Direction.BULL:
            if regime == Regime.BUY_PREMIUM and rrv_val > 0:
                return StrategyType.BUY_CALL
            if regime == Regime.SELL_PREMIUM:
                return StrategyType.BULL_PUT_SPREAD
            return StrategyType.BULL_CALL_SPREAD
        if direction == Direction.BEAR:
            if regime == Regime.BUY_PREMIUM and rrv_val < 0:
                return StrategyType.BUY_PUT
            if regime == Regime.SELL_PREMIUM:
                return StrategyType.BEAR_CALL_SPREAD
            return StrategyType.BEAR_PUT_SPREAD
        return StrategyType.NONE

    def _select_contracts(
        self,
        strategy: StrategyType,
        contracts: List,
        iv_ref: Optional[float],
    ) -> List[OptionLeg]:
        cfg = self.config
        if strategy == StrategyType.BUY_CALL:
            leg = select_long_call(contracts, cfg, iv_ref)
            return [leg] if leg else []
        if strategy == StrategyType.BUY_PUT:
            leg = select_long_put(contracts, cfg, iv_ref)
            return [leg] if leg else []
        if strategy == StrategyType.BULL_PUT_SPREAD:
            legs = select_credit_spread(contracts, cfg, OptionType.PUT)
            return legs or []
        if strategy == StrategyType.BEAR_CALL_SPREAD:
            legs = select_credit_spread(contracts, cfg, OptionType.CALL)
            return legs or []
        if strategy == StrategyType.BULL_CALL_SPREAD:
            legs = select_debit_spread(contracts, cfg, OptionType.CALL, iv_ref)
            return legs or []
        if strategy == StrategyType.BEAR_PUT_SPREAD:
            legs = select_debit_spread(contracts, cfg, OptionType.PUT, iv_ref)
            return legs or []
        return []

    def _exit_rules(self, strategy: StrategyType) -> dict:
        cfg = self.config
        if strategy in (StrategyType.BUY_CALL, StrategyType.BUY_PUT):
            return {
                "time_stop_min": cfg.time_stop_min,
                "profit_target": cfg.profit_target_long,
                "stop_loss": cfg.stop_loss_long,
                "indicator_flip": True,
            }
        return {
            "time_stop_min": cfg.time_stop_min,
            "profit_target": cfg.profit_target_spread,
            "stop_loss": cfg.stop_loss_spread,
            "indicator_flip": True,
        }

    def _sector_index(self, symbol: str) -> str:
        indices = self.ticker_index_repo.get_indices_for_stock(symbol)
        default = self.settings.nifty_symbol
        for idx in indices:
            if idx != default:
                return idx
        return default

    def _fetch_chain(self, symbol: str) -> tuple[Optional[dict], Optional[str]]:
        # fetch expiries
        expiry_payload = self.live_data.fetch_expiries(
            exchange=self.settings.groww_exchange,
            underlying_symbol=symbol,
            year=None,
            month=None,
        )
        expiries = expiry_payload.get("expiries") if isinstance(expiry_payload, dict) else None
        expiry_date = _select_expiry(expiries, self.config.min_dte_days)
        if expiry_date is None:
            return None, None

        # fetch option chain
        chain = self.live_data.fetch_live(
            symbol=symbol,
            exchange=self.settings.groww_exchange,
            segment=self.settings.groww_segment,
            expiry_date=expiry_date,
            underlying=symbol,
        )
        raw_chain = chain.get("options_chain") if isinstance(chain, dict) else None
        if raw_chain is None:
            return None, expiry_date
        return raw_chain, expiry_date


def _compute_rrs(sym: Dict[str, np.ndarray], bench: Dict[str, np.ndarray]) -> Optional[float]:
    sym_aligned, ben_aligned, common_ts = align_ohlcv(sym, bench)
    if common_ts.size < 30:
        return None
    sym_ohlc = {k: sym_aligned[k] for k in ["high", "low", "close"]}
    ben_ohlc = {k: ben_aligned[k] for k in ["high", "low", "close"]}
    series = rrs(sym_ohlc, ben_ohlc, length=12)
    return float(series[-1])


def _compute_rrv(sym: Dict[str, np.ndarray], bench: Dict[str, np.ndarray]) -> Optional[float]:
    sym_aligned, ben_aligned, common_ts = align_ohlcv(sym, bench)
    if common_ts.size < 30:
        return None
    series = rrv(sym_aligned["volume"], ben_aligned["volume"], length=12, use_log=True)
    return float(series[-1])


def _compute_rve(sym: Dict[str, np.ndarray], bench: Dict[str, np.ndarray]) -> Optional[float]:
    sym_aligned, ben_aligned, common_ts = align_ohlcv(sym, bench)
    if common_ts.size < 30:
        return None
    sym_ohlc = {k: sym_aligned[k] for k in ["high", "low", "close"]}
    ben_ohlc = {k: ben_aligned[k] for k in ["high", "low", "close"]}
    series = rve(sym_ohlc, ben_ohlc, length=12, atr_period=14, smooth_atr=1)
    return float(series[-1])


def _parse_time(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def _tzinfo(name: str):
    from zoneinfo import ZoneInfo
    return ZoneInfo(name)


def _select_expiry(expiries: Optional[List[str]] | dict, min_dte: int) -> Optional[str]:
    if not expiries:
        return None

    if isinstance(expiries, dict):
        candidates = expiries.get("expiries") or expiries.get("data") or []
    else:
        candidates = expiries

    now = datetime.now(_tzinfo("Asia/Kolkata"))
    parsed = []
    for exp in candidates:
        if not exp:
            continue
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y"):
            try:
                dt = datetime.strptime(exp, fmt)
                dt = dt.replace(tzinfo=now.tzinfo)
                parsed.append(dt)
                break
            except ValueError:
                continue
        else:
            try:
                dt = datetime.fromisoformat(exp)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=now.tzinfo)
                parsed.append(dt)
            except ValueError:
                continue

    if not parsed:
        return None

    parsed.sort()
    for dt in parsed:
        if (dt.date() - now.date()).days >= min_dte:
            return dt.date().isoformat()
    return parsed[0].date().isoformat()


def _days_to_expiry(expiry_date: str, now: datetime) -> int:
    try:
        exp = datetime.fromisoformat(expiry_date).date()
        return (exp - now.date()).days
    except ValueError:
        return 0
