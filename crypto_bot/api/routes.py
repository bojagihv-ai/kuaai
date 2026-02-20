"""FastAPI routes + WebSocket real-time data."""
import asyncio
import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..exchanges import UpbitExchange, BybitExchange
from ..strategies import AutoStrategy, AutoStrategyConfig, UserStrategy, UserStrategyConfig, compute_indicators
from ..arbitrage import KimchiPremiumMonitor
from ..data import database as db

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Global state (단순화 - 프로덕션에서는 상태 관리 레이어 분리) ─────────────
_state: dict = {
    "upbit": None,
    "bybit_spot": None,
    "bybit_futures": None,
    "auto_strategy": None,
    "user_strategy": None,
    "kimchi_monitor": None,
    "dry_run": True,
    "bot_running": False,
    "monitor_task": None,
}
_ws_clients: list[WebSocket] = []


# ── WebSocket broadcast ────────────────────────────────────────────────────────
async def broadcast(data: dict):
    dead = []
    for ws in _ws_clients:
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.remove(ws)


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _ws_clients.append(ws)
    logger.info(f"WebSocket client connected. Total: {len(_ws_clients)}")
    try:
        while True:
            await ws.receive_text()   # keep-alive ping from client
    except WebSocketDisconnect:
        _ws_clients.remove(ws)
        logger.info("WebSocket client disconnected")


# ── Config models ─────────────────────────────────────────────────────────────
class ExchangeKeys(BaseModel):
    upbit_key: str = ""
    upbit_secret: str = ""
    bybit_key: str = ""
    bybit_secret: str = ""
    dry_run: bool = True


class AutoStrategyRequest(BaseModel):
    symbol: str = "KRW-BTC"
    interval: str = "15m"
    base_invest_ratio: float = 0.10
    max_invest_ratio: float = 0.50
    stop_loss_pct: float = 3.0
    take_profit_pct: float = 5.0
    trailing_stop_pct: float = 2.0
    min_score_buy: float = 40.0
    max_score_sell: float = -40.0
    trade_cooldown: int = 300


class UserStrategyRequest(BaseModel):
    name: str = "내 전략"
    buy_rsi_below: Optional[float] = 35.0
    buy_macd_cross: bool = True
    buy_bb_below: bool = True
    buy_score_threshold: float = 35.0
    sell_rsi_above: Optional[float] = 70.0
    sell_macd_cross: bool = True
    stop_loss_pct: float = 3.0
    take_profit_pct: float = 5.0
    use_trailing_stop: bool = True
    trailing_stop_pct: float = 2.0
    base_invest_ratio: float = 0.10
    max_total_ratio: float = 0.60
    dca_levels: list = []
    trade_cooldown_sec: int = 300
    interval: str = "15m"


class ArbitrageConfig(BaseModel):
    min_profit_pct: float = 0.3
    trade_amount_krw: float = 1_000_000
    auto_trade: bool = False


# ── Setup endpoints ────────────────────────────────────────────────────────────
@router.post("/api/setup")
async def setup_exchanges(keys: ExchangeKeys):
    _state["upbit"] = UpbitExchange(keys.upbit_key, keys.upbit_secret)
    _state["bybit_spot"] = BybitExchange(keys.bybit_key, keys.bybit_secret, "spot")
    _state["bybit_futures"] = BybitExchange(keys.bybit_key, keys.bybit_secret, "linear")
    _state["dry_run"] = keys.dry_run

    # Save to DB
    db.save_config("exchange_keys", {
        "upbit_key": keys.upbit_key[:8] + "***",
        "bybit_key": keys.bybit_key[:8] + "***",
        "dry_run": keys.dry_run,
    })

    return {"status": "ok", "dry_run": keys.dry_run}


@router.get("/api/status")
async def get_status():
    return {
        "exchanges_configured": _state["upbit"] is not None,
        "bot_running": _state["bot_running"],
        "dry_run": _state["dry_run"],
        "ws_clients": len(_ws_clients),
        "auto_strategy_active": _state["auto_strategy"] is not None,
        "user_strategy_active": _state["user_strategy"] is not None,
        "kimchi_monitor_active": _state["kimchi_monitor"] is not None,
    }


# ── Market data endpoints ──────────────────────────────────────────────────────
@router.get("/api/ticker")
async def get_ticker(symbol: str = "KRW-BTC", exchange: str = "upbit"):
    ex = _get_exchange(exchange)
    ticker = await ex.get_ticker(symbol)
    return {
        "symbol": ticker.symbol,
        "price": ticker.price,
        "volume_24h": ticker.volume_24h,
        "change_24h": ticker.change_24h,
        "timestamp": ticker.timestamp,
    }


@router.get("/api/ohlcv")
async def get_ohlcv(symbol: str = "KRW-BTC", interval: str = "15m",
                    limit: int = 200, exchange: str = "upbit"):
    ex = _get_exchange(exchange)
    data = await ex.get_ohlcv(symbol, interval, limit)
    return {"symbol": symbol, "interval": interval, "data": data}


@router.get("/api/orderbook")
async def get_orderbook(symbol: str = "KRW-BTC", exchange: str = "upbit"):
    ex = _get_exchange(exchange)
    ob = await ex.get_orderbook(symbol)
    return {"bids": ob.bids, "asks": ob.asks, "timestamp": ob.timestamp}


@router.get("/api/balances")
async def get_balances(exchange: str = "upbit"):
    ex = _get_exchange(exchange)
    balances = await ex.get_balances()
    return [{"currency": b.currency, "available": b.available, "locked": b.locked} for b in balances]


# ── Analysis endpoints ─────────────────────────────────────────────────────────
@router.get("/api/analysis")
async def get_analysis(symbol: str = "KRW-BTC", interval: str = "15m", exchange: str = "upbit"):
    ex = _get_exchange(exchange)
    ohlcv = await ex.get_ohlcv(symbol, interval, 200)
    ticker = await ex.get_ticker(symbol)
    indicators = compute_indicators(ohlcv)
    if not indicators:
        raise HTTPException(400, "Not enough data for analysis")

    return {
        "symbol": symbol,
        "exchange": exchange,
        "price": ticker.price,
        "change_24h": ticker.change_24h,
        "indicators": {
            "rsi": indicators.rsi,
            "macd": indicators.macd,
            "macd_signal": indicators.macd_signal,
            "macd_hist": indicators.macd_hist,
            "bb_upper": indicators.bb_upper,
            "bb_mid": indicators.bb_mid,
            "bb_lower": indicators.bb_lower,
            "ema5": indicators.ema5,
            "ema20": indicators.ema20,
            "ema60": indicators.ema60,
            "ema120": indicators.ema120,
            "volume_ratio": indicators.volume_ratio,
            "stoch_k": indicators.stoch_k,
            "stoch_d": indicators.stoch_d,
            "atr": indicators.atr,
        },
        "trend": indicators.trend,
        "signal": indicators.signal,
        "score": indicators.score,
        "timestamp": time.time(),
    }


@router.get("/api/funding-rate")
async def get_funding_rate(symbol: str = "BTCUSDT"):
    ex = _state.get("bybit_futures")
    if not ex:
        return {"error": "Bybit not configured"}
    fr = await ex.get_funding_rate(symbol)
    if not fr:
        return {"error": "No funding rate data"}
    return {
        "symbol": fr.symbol,
        "rate": fr.rate,
        "rate_pct": fr.rate * 100,
        "next_funding": fr.next_funding,
        "annualized_pct": fr.rate * 3 * 365 * 100,  # 8-hour intervals
    }


# ── Kimchi premium endpoints ───────────────────────────────────────────────────
@router.get("/api/kimchi")
async def get_kimchi():
    if not _ensure_kimchi():
        raise HTTPException(400, "Exchanges not configured")
    opp = await _state["kimchi_monitor"].check()
    return {
        "upbit_price": opp.upbit_price_krw,
        "bybit_price_usdt": opp.bybit_price_usdt,
        "bybit_price_krw": opp.bybit_price_krw,
        "usd_krw": opp.usd_krw_rate,
        "kimchi_pct": opp.kimchi_premium_pct,
        "net_profit_pct": opp.net_profit_pct,
        "is_profitable": opp.is_profitable,
        "direction": opp.direction,
        "note": opp.note,
        "timestamp": opp.timestamp,
    }


@router.get("/api/kimchi/stats")
async def get_kimchi_stats():
    if not _state["kimchi_monitor"]:
        return {"error": "Monitor not running"}
    return _state["kimchi_monitor"].get_stats()


@router.post("/api/kimchi/config")
async def set_kimchi_config(cfg: ArbitrageConfig):
    if not _ensure_kimchi():
        raise HTTPException(400, "Exchanges not configured")
    monitor = _state["kimchi_monitor"]
    monitor.min_profit_pct = cfg.min_profit_pct
    monitor.trade_amount_krw = cfg.trade_amount_krw
    monitor.auto_trade = cfg.auto_trade
    return {"status": "ok", "config": cfg.dict()}


# ── Strategy endpoints ─────────────────────────────────────────────────────────
@router.post("/api/strategy/auto/config")
async def set_auto_config(req: AutoStrategyRequest):
    ex = _get_exchange("upbit")
    cfg = AutoStrategyConfig(
        symbol=req.symbol,
        interval=req.interval,
        base_invest_ratio=req.base_invest_ratio,
        max_invest_ratio=req.max_invest_ratio,
        stop_loss_pct=req.stop_loss_pct / 100,
        take_profit_pct=req.take_profit_pct / 100,
        trailing_stop_pct=req.trailing_stop_pct / 100,
        min_score_buy=req.min_score_buy,
        max_score_sell=-abs(req.max_score_sell),
        trade_cooldown=req.trade_cooldown,
    )
    _state["auto_strategy"] = AutoStrategy(ex, cfg)
    db.save_config("auto_strategy", req.dict())
    return {"status": "ok", "config": req.dict()}


@router.post("/api/strategy/user/config")
async def set_user_config(req: UserStrategyRequest):
    from ..strategies.user_strategy import DropLevel
    dca = [DropLevel(d["drop_pct"], d["invest_ratio"]) for d in req.dca_levels] if req.dca_levels else [
        DropLevel(3.0, 0.05), DropLevel(5.0, 0.10), DropLevel(8.0, 0.15), DropLevel(12.0, 0.20)
    ]
    cfg = UserStrategyConfig(
        name=req.name,
        buy_rsi_below=req.buy_rsi_below,
        buy_macd_cross=req.buy_macd_cross,
        buy_bb_below=req.buy_bb_below,
        buy_score_threshold=req.buy_score_threshold,
        sell_rsi_above=req.sell_rsi_above,
        sell_macd_cross=req.sell_macd_cross,
        stop_loss_pct=req.stop_loss_pct,
        take_profit_pct=req.take_profit_pct,
        use_trailing_stop=req.use_trailing_stop,
        trailing_stop_pct=req.trailing_stop_pct,
        base_invest_ratio=req.base_invest_ratio,
        max_total_ratio=req.max_total_ratio,
        dca_levels=dca,
        trade_cooldown_sec=req.trade_cooldown_sec,
        interval=req.interval,
    )
    _state["user_strategy"] = UserStrategy(cfg)
    db.save_config("user_strategy", cfg.to_dict())
    return {"status": "ok", "config": cfg.to_dict()}


@router.get("/api/strategy/auto/analyze")
async def auto_analyze(symbol: str = "KRW-BTC", interval: str = "15m"):
    if not _state.get("auto_strategy"):
        ex = _get_exchange("upbit")
        cfg = AutoStrategyConfig(symbol=symbol, interval=interval)
        _state["auto_strategy"] = AutoStrategy(ex, cfg)
    result = await _state["auto_strategy"].analyze()
    return result


@router.get("/api/strategy/auto/stats")
async def auto_stats():
    if not _state.get("auto_strategy"):
        return {"error": "Strategy not configured"}
    return _state["auto_strategy"].get_stats()


# ── Bot control ────────────────────────────────────────────────────────────────
@router.post("/api/bot/start")
async def start_bot(background_tasks: BackgroundTasks, seed_krw: float = 1_000_000):
    if _state["bot_running"]:
        return {"status": "already_running"}
    if not _state["upbit"]:
        raise HTTPException(400, "Exchange not configured")
    _state["bot_running"] = True
    background_tasks.add_task(_run_bot_loop, seed_krw)
    return {"status": "started", "dry_run": _state["dry_run"], "seed_krw": seed_krw}


@router.post("/api/bot/stop")
async def stop_bot():
    _state["bot_running"] = False
    return {"status": "stopped"}


@router.get("/api/trades")
async def get_trades(limit: int = 50):
    return db.get_trades(limit)


@router.get("/api/pnl")
async def get_pnl():
    return db.get_pnl_summary()


# ── Internal helpers ───────────────────────────────────────────────────────────
def _get_exchange(name: str) -> UpbitExchange | BybitExchange:
    key = {"upbit": "upbit", "bybit": "bybit_spot", "bybit_futures": "bybit_futures"}.get(name, name)
    ex = _state.get(key)
    if not ex:
        # Return demo exchange (no API key) for public data
        if name == "upbit":
            _state["upbit"] = UpbitExchange()
            return _state["upbit"]
        elif name in ("bybit", "bybit_spot"):
            _state["bybit_spot"] = BybitExchange()
            return _state["bybit_spot"]
        elif name == "bybit_futures":
            _state["bybit_futures"] = BybitExchange(category="linear")
            return _state["bybit_futures"]
        raise HTTPException(400, f"Exchange '{name}' not configured")
    return ex


def _ensure_kimchi() -> bool:
    if not _state["upbit"] or not _state["bybit_spot"]:
        _state["upbit"] = _state["upbit"] or UpbitExchange()
        _state["bybit_spot"] = _state["bybit_spot"] or BybitExchange()
    if not _state["kimchi_monitor"]:
        _state["kimchi_monitor"] = KimchiPremiumMonitor(
            _state["upbit"], _state["bybit_spot"]
        )
    return True


async def _run_bot_loop(seed_krw: float):
    """Main trading loop - runs in background."""
    logger.info(f"Bot loop started | seed={seed_krw:,.0f}KRW | dry_run={_state['dry_run']}")
    _ensure_kimchi()

    while _state["bot_running"]:
        try:
            # 1) Auto strategy signal
            if _state.get("auto_strategy"):
                result = await _state["auto_strategy"].analyze()
                await broadcast({"type": "analysis", "data": result})
                db.save_signal(
                    "upbit",
                    result.get("symbol", ""),
                    result.get("signal", ""),
                    result.get("score", 0),
                    result.get("price", 0),
                    result.get("indicators", {}),
                )

                # Execute trade
                trade = await _state["auto_strategy"].execute_signal(
                    seed_krw, dry_run=_state["dry_run"]
                )
                if trade:
                    db.save_trade(
                        "upbit", trade.symbol, trade.side, trade.price, trade.qty,
                        trade.krw_amount, trade.fee, trade.pnl, trade.order_id,
                        "auto", trade.note, _state["dry_run"]
                    )
                    await broadcast({"type": "trade", "data": {
                        "side": trade.side, "price": trade.price,
                        "qty": trade.qty, "pnl": trade.pnl, "note": trade.note
                    }})

            # 2) Kimchi premium check
            if _state.get("kimchi_monitor"):
                opp = await _state["kimchi_monitor"].check()
                await broadcast({"type": "kimchi", "data": {
                    "kimchi_pct": opp.kimchi_premium_pct,
                    "net_profit_pct": opp.net_profit_pct,
                    "is_profitable": opp.is_profitable,
                    "direction": opp.direction,
                    "usd_krw": opp.usd_krw_rate,
                    "upbit_price": opp.upbit_price_krw,
                    "bybit_price_krw": opp.bybit_price_krw,
                }})
                if opp.is_profitable:
                    db.save_arbitrage(
                        opp.kimchi_premium_pct, opp.net_profit_pct, opp.direction,
                        opp.upbit_price_krw, opp.bybit_price_krw, opp.usd_krw_rate,
                        _state["kimchi_monitor"].trade_amount_krw, 0, "detected"
                    )

            await asyncio.sleep(30)  # 30초마다 실행

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Bot loop error: {e}", exc_info=True)
            await broadcast({"type": "error", "data": {"message": str(e)}})
            await asyncio.sleep(10)

    logger.info("Bot loop stopped")
