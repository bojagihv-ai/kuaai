"""
김프(김치 프리미엄) 모니터 + 자동 차익거래 엔진.

김프 = (업비트KRW가격 - 바이비트USDT가격 * USD/KRW환율) / (바이비트USDT가격 * 환율) * 100

차익거래 방향:
  김프 양수(+) = 업비트가 비쌈 → 업비트에서 팔고, 바이비트에서 삼
  김프 음수(-) = 해외프리미엄  → 업비트에서 사고, 바이비트에서 팔기 (선물 숏)
"""
import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional

import aiohttp

from ..exchanges.upbit import UpbitExchange
from ..exchanges.bybit import BybitExchange

logger = logging.getLogger(__name__)

# 환율 API (무료 오픈 소스)
FX_URL = "https://open.er-api.com/v6/latest/USD"


@dataclass
class ArbitrageOpportunity:
    timestamp: float
    upbit_price_krw: float      # 업비트 BTC/KRW
    bybit_price_usdt: float     # 바이비트 BTC/USDT
    usd_krw_rate: float         # 달러/원 환율
    bybit_price_krw: float      # 바이비트 원화 환산가
    kimchi_premium_pct: float   # 김프 %
    upbit_fee_pct: float = 0.05
    bybit_fee_pct: float = 0.055
    # Net profit after fees
    net_profit_pct: float = 0.0
    is_profitable: bool = False
    direction: str = ""         # 'kimchi_buy_bybit' | 'reverse_buy_upbit'
    note: str = ""


@dataclass
class ArbitrageResult:
    opportunity: ArbitrageOpportunity
    trade_amount_krw: float
    expected_profit_krw: float
    upbit_order_id: str = ""
    bybit_order_id: str = ""
    status: str = "pending"    # 'pending' | 'executed' | 'failed'
    actual_profit_krw: float = 0.0
    error: str = ""


class KimchiPremiumMonitor:
    def __init__(
        self,
        upbit: UpbitExchange,
        bybit: BybitExchange,
        min_profit_pct: float = 0.3,   # 수수료 공제 후 최소 수익률 %
        trade_amount_krw: float = 1_000_000,  # 1회 거래 금액 (원)
        auto_trade: bool = False,
    ):
        self.upbit = upbit
        self.bybit = bybit
        self.min_profit_pct = min_profit_pct
        self.trade_amount_krw = trade_amount_krw
        self.auto_trade = auto_trade
        self._usd_krw: float = 1350.0   # 기본 환율 (자동 갱신)
        self._last_fx_update: float = 0
        self.history: list[ArbitrageOpportunity] = []
        self.trade_history: list[ArbitrageResult] = []

    async def update_fx_rate(self) -> float:
        """달러/원 환율 업데이트 (60초 캐시)."""
        if time.time() - self._last_fx_update < 60:
            return self._usd_krw
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(FX_URL, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    data = await resp.json()
                    self._usd_krw = data["rates"]["KRW"]
                    self._last_fx_update = time.time()
                    logger.debug(f"FX rate updated: 1 USD = {self._usd_krw:,.2f} KRW")
        except Exception as e:
            logger.warning(f"FX rate fetch failed, using cached: {e}")
        return self._usd_krw

    async def check(self) -> ArbitrageOpportunity:
        """현재 김프 계산."""
        usd_krw, upbit_ticker, bybit_ticker = await asyncio.gather(
            self.update_fx_rate(),
            self.upbit.get_ticker("KRW-BTC"),
            self.bybit.get_ticker("BTCUSDT"),
        )

        upbit_price = upbit_ticker.price
        bybit_price_usdt = bybit_ticker.price
        bybit_price_krw = bybit_price_usdt * usd_krw

        kimchi_pct = (upbit_price - bybit_price_krw) / bybit_price_krw * 100

        # 수수료 계산 (왕복)
        total_fee_pct = (self.upbit.taker_fee + self.bybit.taker_fee) * 2 * 100  # round trip
        net_profit_pct = abs(kimchi_pct) - total_fee_pct

        is_profitable = net_profit_pct >= self.min_profit_pct

        if kimchi_pct > 0:
            direction = "kimchi_buy_bybit"  # 바이비트에서 사고 업비트에서 팔기
            note = f"김프 +{kimchi_pct:.2f}% → 바이비트 매수/업비트 매도"
        else:
            direction = "reverse_buy_upbit"  # 역김프: 업비트에서 사고 바이비트에서 공매도
            note = f"역김프 {kimchi_pct:.2f}% → 업비트 매수/바이비트 숏"

        opp = ArbitrageOpportunity(
            timestamp=time.time(),
            upbit_price_krw=upbit_price,
            bybit_price_usdt=bybit_price_usdt,
            usd_krw_rate=usd_krw,
            bybit_price_krw=bybit_price_krw,
            kimchi_premium_pct=round(kimchi_pct, 4),
            upbit_fee_pct=self.upbit.taker_fee * 100,
            bybit_fee_pct=self.bybit.taker_fee * 100,
            net_profit_pct=round(net_profit_pct, 4),
            is_profitable=is_profitable,
            direction=direction,
            note=note,
        )

        self.history.append(opp)
        if len(self.history) > 1000:
            self.history = self.history[-500:]

        if is_profitable and self.auto_trade:
            await self.execute_arbitrage(opp)

        return opp

    async def execute_arbitrage(self, opp: ArbitrageOpportunity) -> ArbitrageResult:
        """
        실제 차익거래 실행.
        ※ 김프 방향 (양수): 업비트에서 BTC 보유 필요, 바이비트에서 USDT 필요
        ※ 역김프 방향 (음수): 업비트에서 KRW 필요, 바이비트 선물 숏 포지션
        """
        result = ArbitrageResult(
            opportunity=opp,
            trade_amount_krw=self.trade_amount_krw,
            expected_profit_krw=self.trade_amount_krw * opp.net_profit_pct / 100,
        )

        try:
            qty_btc = self.trade_amount_krw / opp.upbit_price_krw
            qty_btc = round(qty_btc, 8)

            if opp.direction == "kimchi_buy_bybit":
                # 1) 업비트 BTC 매도 (KRW 확보)
                upbit_order = await self.upbit.place_order(
                    "KRW-BTC", "ask", "market", qty=qty_btc
                )
                result.upbit_order_id = upbit_order.order_id

                # 2) 바이비트 BTC 매수 (USDT 소비)
                qty_usdt_equiv = qty_btc  # Bybit uses BTC qty for linear
                bybit_order = await self.bybit.place_order(
                    "BTCUSDT", "buy", "Market", qty=round(qty_btc, 3)
                )
                result.bybit_order_id = bybit_order.order_id

            else:  # reverse_buy_upbit
                # 1) 업비트 BTC 매수
                upbit_order = await self.upbit.place_order(
                    "KRW-BTC", "bid", "price", krw_amount=self.trade_amount_krw
                )
                result.upbit_order_id = upbit_order.order_id

                # 2) 바이비트 선물 숏 (헤지)
                bybit_order = await self.bybit.place_order(
                    "BTCUSDT", "sell", "Market", qty=round(qty_btc, 3)
                )
                result.bybit_order_id = bybit_order.order_id

            result.status = "executed"
            result.actual_profit_krw = result.expected_profit_krw
            logger.info(
                f"차익거래 실행: {opp.direction} | 김프={opp.kimchi_premium_pct:.2f}% | "
                f"예상수익={result.expected_profit_krw:,.0f}KRW"
            )

        except Exception as e:
            result.status = "failed"
            result.error = str(e)
            logger.error(f"차익거래 실패: {e}")

        self.trade_history.append(result)
        return result

    def get_stats(self) -> dict:
        if not self.history:
            return {"avg_kimchi": 0, "current_kimchi": 0, "opportunities": 0}

        last = self.history[-1]
        recent = self.history[-20:]

        executed = [t for t in self.trade_history if t.status == "executed"]
        total_profit = sum(t.actual_profit_krw for t in executed)

        return {
            "current_kimchi_pct": last.kimchi_premium_pct,
            "current_net_profit_pct": last.net_profit_pct,
            "current_direction": last.direction,
            "upbit_price": last.upbit_price_krw,
            "bybit_price_krw": last.bybit_price_krw,
            "usd_krw": last.usd_krw_rate,
            "is_profitable": last.is_profitable,
            "avg_kimchi_pct_20": round(sum(h.kimchi_premium_pct for h in recent) / len(recent), 4),
            "total_arb_trades": len(executed),
            "total_arb_profit_krw": total_profit,
            "note": last.note,
        }
