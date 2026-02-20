"""Auto trading strategy - AI-like rule-based system."""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from ..exchanges.base import BaseExchange
from .indicators import compute_indicators, IndicatorResult

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    symbol: str
    side: str
    price: float
    qty: float
    krw_amount: float
    fee: float
    timestamp: float
    order_id: str = ""
    pnl: float = 0.0
    note: str = ""


@dataclass
class AutoStrategyConfig:
    symbol: str = "KRW-BTC"
    interval: str = "15m"
    # Position sizing
    base_invest_ratio: float = 0.1   # 시드의 10% 기본 투자
    max_invest_ratio: float = 0.5    # 최대 50%
    # Entry signals
    min_score_buy: float = 40.0      # 매수 최소 점수
    max_score_sell: float = -40.0    # 매도 최대 점수
    # Risk management
    stop_loss_pct: float = 0.03      # 3% 손절
    take_profit_pct: float = 0.05    # 5% 익절
    trailing_stop_pct: float = 0.02  # 2% 트레일링
    # RSI based DCA
    rsi_dca_levels: list = field(default_factory=lambda: [
        {"rsi_below": 40, "extra_ratio": 0.05},
        {"rsi_below": 30, "extra_ratio": 0.10},
        {"rsi_below": 20, "extra_ratio": 0.15},
    ])
    # Cooldown between trades (seconds)
    trade_cooldown: int = 300


class AutoStrategy:
    def __init__(self, exchange: BaseExchange, config: AutoStrategyConfig):
        self.exchange = exchange
        self.cfg = config
        self.position: Optional[dict] = None   # {price, qty, high_price}
        self.last_trade_time: float = 0
        self.trade_history: list[TradeRecord] = []
        self.running = False
        self._task = None

    async def analyze(self) -> dict:
        """Run full analysis and return recommendation."""
        ohlcv = await self.exchange.get_ohlcv(self.cfg.symbol, self.cfg.interval, 200)
        ticker = await self.exchange.get_ticker(self.cfg.symbol)
        indicators = compute_indicators(ohlcv)
        if not indicators:
            return {"error": "Not enough data"}

        price = ticker.price
        result = {
            "symbol": self.cfg.symbol,
            "price": price,
            "timestamp": time.time(),
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
            "recommendation": self._build_recommendation(price, indicators),
        }
        return result

    def _build_recommendation(self, price: float, ind: IndicatorResult) -> dict:
        reasons = []
        action = "hold"

        if ind.score >= self.cfg.min_score_buy:
            action = "buy"
            if ind.rsi < 30:
                reasons.append(f"RSI 과매도 ({ind.rsi:.1f})")
            if ind.macd_hist > 0:
                reasons.append("MACD 골든크로스")
            if price < ind.bb_lower:
                reasons.append("볼린저 하단 이탈 (반등 기대)")
            if ind.ema5 > ind.ema20:
                reasons.append("단기 EMA 상향")
            if ind.volume_ratio > 1.5:
                reasons.append(f"거래량 급증 ({ind.volume_ratio:.1f}x)")
        elif ind.score <= self.cfg.max_score_sell:
            action = "sell"
            if ind.rsi > 70:
                reasons.append(f"RSI 과매수 ({ind.rsi:.1f})")
            if ind.macd_hist < 0:
                reasons.append("MACD 데드크로스")
            if price > ind.bb_upper:
                reasons.append("볼린저 상단 돌파 (조정 가능)")
            if ind.ema5 < ind.ema20:
                reasons.append("단기 EMA 하향")

        # Stop loss / take profit check
        if self.position:
            entry = self.position["price"]
            pnl_pct = (price - entry) / entry
            if pnl_pct <= -self.cfg.stop_loss_pct:
                action = "sell"
                reasons = [f"손절 ({pnl_pct*100:.1f}%)"]
            elif pnl_pct >= self.cfg.take_profit_pct:
                action = "sell"
                reasons = [f"익절 ({pnl_pct*100:.1f}%)"]
            # Trailing stop
            high_price = self.position.get("high_price", entry)
            if price > high_price:
                self.position["high_price"] = price
            elif (high_price - price) / high_price >= self.cfg.trailing_stop_pct:
                action = "sell"
                reasons = [f"트레일링 스탑 (고점 대비 -{self.cfg.trailing_stop_pct*100:.0f}%)"]

        if not reasons:
            reasons.append("명확한 신호 없음 - 관망")

        return {
            "action": action,
            "reasons": reasons,
            "score": ind.score,
            "confidence": min(abs(ind.score) / 100 * 100, 100),
        }

    def calc_invest_amount(self, seed: float, indicators: IndicatorResult) -> float:
        """RSI 기반 DCA 투자 비율 계산."""
        ratio = self.cfg.base_invest_ratio
        for level in sorted(self.cfg.rsi_dca_levels, key=lambda x: x["rsi_below"]):
            if indicators.rsi < level["rsi_below"]:
                ratio += level["extra_ratio"]
        ratio = min(ratio, self.cfg.max_invest_ratio)
        return seed * ratio

    async def execute_signal(self, seed_krw: float, dry_run: bool = True) -> Optional[TradeRecord]:
        """Execute buy/sell based on analysis."""
        cooldown_left = (self.last_trade_time + self.cfg.trade_cooldown) - time.time()
        if cooldown_left > 0:
            logger.info(f"Trade cooldown: {cooldown_left:.0f}s remaining")
            return None

        result = await self.analyze()
        if "error" in result:
            return None

        rec = result["recommendation"]
        indicators_data = result["indicators"]
        price = result["price"]
        action = rec["action"]

        if action == "buy" and not self.position:
            # Calculate invest amount
            class _Ind:
                rsi = indicators_data["rsi"]
            invest_krw = self.calc_invest_amount(seed_krw, _Ind())
            fee = invest_krw * self.exchange.taker_fee
            actual_krw = invest_krw - fee
            qty = actual_krw / price

            if not dry_run:
                order = await self.exchange.place_order(
                    self.cfg.symbol, "bid", "price", krw_amount=invest_krw
                )
                order_id = order.order_id
            else:
                order_id = f"dry_{int(time.time())}"

            self.position = {"price": price, "qty": qty, "high_price": price}
            self.last_trade_time = time.time()

            record = TradeRecord(
                symbol=self.cfg.symbol,
                side="buy",
                price=price,
                qty=qty,
                krw_amount=invest_krw,
                fee=fee,
                timestamp=time.time(),
                order_id=order_id,
                note=f"점수:{result['score']} | {' | '.join(rec['reasons'][:2])}",
            )
            self.trade_history.append(record)
            logger.info(f"{'[DRY]' if dry_run else ''} BUY {self.cfg.symbol} qty={qty:.6f} price={price:,.0f} invest={invest_krw:,.0f}KRW")
            return record

        elif action == "sell" and self.position:
            qty = self.position["qty"]
            proceeds = qty * price
            fee = proceeds * self.exchange.taker_fee
            entry_price = self.position["price"]
            pnl = proceeds - fee - (entry_price * qty)

            if not dry_run:
                order = await self.exchange.place_order(self.cfg.symbol, "ask", "market", qty=qty)
                order_id = order.order_id
            else:
                order_id = f"dry_{int(time.time())}"

            self.last_trade_time = time.time()
            self.position = None

            record = TradeRecord(
                symbol=self.cfg.symbol,
                side="sell",
                price=price,
                qty=qty,
                krw_amount=proceeds,
                fee=fee,
                timestamp=time.time(),
                order_id=order_id,
                pnl=pnl,
                note=f"손익:{pnl:+,.0f}KRW | {' | '.join(rec['reasons'][:2])}",
            )
            self.trade_history.append(record)
            logger.info(f"{'[DRY]' if dry_run else ''} SELL {self.cfg.symbol} qty={qty:.6f} price={price:,.0f} PnL={pnl:+,.0f}KRW")
            return record

        return None

    def get_stats(self) -> dict:
        if not self.trade_history:
            return {"total_trades": 0, "win_rate": 0, "total_pnl": 0}
        sells = [t for t in self.trade_history if t.side == "sell"]
        wins = [t for t in sells if t.pnl > 0]
        total_pnl = sum(t.pnl for t in sells)
        total_fee = sum(t.fee for t in self.trade_history)
        return {
            "total_trades": len(self.trade_history),
            "buy_count": len([t for t in self.trade_history if t.side == "buy"]),
            "sell_count": len(sells),
            "win_count": len(wins),
            "lose_count": len(sells) - len(wins),
            "win_rate": len(wins) / len(sells) * 100 if sells else 0,
            "total_pnl": total_pnl,
            "total_fee": total_fee,
            "net_pnl": total_pnl - total_fee,
            "in_position": self.position is not None,
        }
