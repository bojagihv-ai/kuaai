"""Bybit V5 exchange connector (spot + linear futures)."""
import hashlib
import hmac
import time
import logging
from typing import Optional

import aiohttp

from .base import BaseExchange, Ticker, OrderBook, Balance, Order, FundingRate

logger = logging.getLogger(__name__)

BYBIT_BASE = "https://api.bybit.com"


class BybitExchange(BaseExchange):
    name = "bybit"
    taker_fee = 0.00055   # 0.055% spot
    maker_fee = 0.0001

    SPOT_TAKER = 0.00055
    FUTURES_TAKER = 0.00055
    FUTURES_MAKER = 0.0002

    def __init__(self, api_key: str = "", secret: str = "", category: str = "spot"):
        super().__init__(api_key, secret)
        self.category = category  # 'spot' | 'linear'

    # ── Internal helpers ─────────────────────────────────────────────────────
    def _sign(self, params_str: str, timestamp: int, recv_window: int = 5000) -> str:
        pre_hash = f"{timestamp}{self.api_key}{recv_window}{params_str}"
        return hmac.new(self.secret.encode(), pre_hash.encode(), hashlib.sha256).hexdigest()

    def _auth_headers(self, params_str: str = "") -> dict:
        ts = int(time.time() * 1000)
        recv_window = 5000
        return {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": str(ts),
            "X-BAPI-RECV-WINDOW": str(recv_window),
            "X-BAPI-SIGN": self._sign(params_str, ts, recv_window),
            "Content-Type": "application/json",
        }

    async def _get(self, path: str, params: dict = None, auth: bool = False):
        params = params or {}
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        headers = self._auth_headers(query) if auth else {}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BYBIT_BASE}{path}",
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                if data.get("retCode", 0) != 0:
                    raise Exception(f"Bybit API error: {data.get('retMsg')}")
                return data["result"]

    async def _post(self, path: str, body: dict, auth: bool = True):
        import json
        body_str = json.dumps(body)
        headers = self._auth_headers(body_str) if auth else {"Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BYBIT_BASE}{path}",
                data=body_str,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                if data.get("retCode", 0) != 0:
                    raise Exception(f"Bybit API error: {data.get('retMsg')}")
                return data["result"]

    # ── Market data ──────────────────────────────────────────────────────────
    async def get_ticker(self, symbol: str = "BTCUSDT") -> Ticker:
        data = await self._get(
            "/v5/market/tickers", {"category": self.category, "symbol": symbol}
        )
        d = data["list"][0]
        return Ticker(
            symbol=symbol,
            price=float(d["lastPrice"]),
            volume_24h=float(d.get("volume24h", d.get("turnover24h", 0))),
            change_24h=float(d.get("price24hPcnt", 0)) * 100,
            timestamp=time.time(),
        )

    async def get_orderbook(self, symbol: str = "BTCUSDT", depth: int = 10) -> OrderBook:
        data = await self._get(
            "/v5/market/orderbook",
            {"category": self.category, "symbol": symbol, "limit": depth},
        )
        bids = [[float(p), float(q)] for p, q in data["b"]]
        asks = [[float(p), float(q)] for p, q in data["a"]]
        return OrderBook(bids=bids, asks=asks, timestamp=time.time())

    async def get_ohlcv(self, symbol: str = "BTCUSDT", interval: str = "1", limit: int = 200) -> list:
        # Bybit interval: 1,3,5,15,30,60,120,240,360,720,D,W,M
        interval_map = {
            "1m": "1", "3m": "3", "5m": "5", "15m": "15", "30m": "30",
            "1h": "60", "4h": "240", "1d": "D", "1w": "W",
        }
        iv = interval_map.get(interval, interval)
        data = await self._get(
            "/v5/market/kline",
            {"category": self.category, "symbol": symbol, "interval": iv, "limit": limit},
        )
        candles = data["list"]
        candles = list(reversed(candles))
        return [
            [int(c[0]), float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])]
            for c in candles
        ]

    # ── Funding rate ──────────────────────────────────────────────────────────
    async def get_funding_rate(self, symbol: str = "BTCUSDT") -> Optional[FundingRate]:
        if self.category != "linear":
            return None
        try:
            data = await self._get(
                "/v5/market/tickers", {"category": "linear", "symbol": symbol}
            )
            d = data["list"][0]
            return FundingRate(
                symbol=symbol,
                rate=float(d.get("fundingRate", 0)),
                next_funding=float(d.get("nextFundingTime", 0)) / 1000,
            )
        except Exception as e:
            logger.warning(f"Failed to get funding rate: {e}")
            return None

    async def get_historical_funding(self, symbol: str = "BTCUSDT", limit: int = 10) -> list:
        data = await self._get(
            "/v5/market/funding/history",
            {"category": "linear", "symbol": symbol, "limit": limit},
        )
        return [
            {
                "symbol": d["symbol"],
                "rate": float(d["fundingRate"]),
                "timestamp": int(d["fundingRateTimestamp"]) / 1000,
            }
            for d in data["list"]
        ]

    # ── Account ───────────────────────────────────────────────────────────────
    async def get_balances(self, account_type: str = "UNIFIED") -> list[Balance]:
        data = await self._get(
            "/v5/account/wallet-balance",
            {"accountType": account_type},
            auth=True,
        )
        balances = []
        for acct in data.get("list", []):
            for coin in acct.get("coin", []):
                balances.append(
                    Balance(
                        currency=coin["coin"],
                        available=float(coin.get("availableToWithdraw", coin.get("free", 0))),
                        locked=float(coin.get("locked", 0)),
                    )
                )
        return balances

    async def get_positions(self, symbol: str = None) -> list:
        params = {"category": "linear", "settleCoin": "USDT"}
        if symbol:
            params["symbol"] = symbol
        data = await self._get("/v5/position/list", params, auth=True)
        return data.get("list", [])

    # ── Trading ───────────────────────────────────────────────────────────────
    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str = "Market",
        qty: float = None,
        price: Optional[float] = None,
        reduce_only: bool = False,
    ) -> Order:
        body = {
            "category": self.category,
            "symbol": symbol,
            "side": side.capitalize(),  # Buy | Sell
            "orderType": order_type.capitalize(),  # Market | Limit
            "qty": str(qty),
        }
        if order_type.lower() == "limit" and price:
            body["price"] = str(price)
        if reduce_only:
            body["reduceOnly"] = True

        data = await self._post("/v5/order/create", body)
        return Order(
            order_id=data.get("orderId", ""),
            symbol=symbol,
            side=side.lower(),
            order_type=order_type.lower(),
            price=price or 0,
            qty=qty,
            filled_qty=0,
            status="open",
            timestamp=time.time(),
        )

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        try:
            await self._post(
                "/v5/order/cancel",
                {"category": self.category, "symbol": symbol, "orderId": order_id},
            )
            return True
        except Exception:
            return False

    async def get_order(self, symbol: str, order_id: str) -> Order:
        data = await self._get(
            "/v5/order/realtime",
            {"category": self.category, "symbol": symbol, "orderId": order_id},
            auth=True,
        )
        d = data["list"][0]
        return Order(
            order_id=d["orderId"],
            symbol=d["symbol"],
            side=d["side"].lower(),
            order_type=d["orderType"].lower(),
            price=float(d.get("price", 0)),
            qty=float(d.get("qty", 0)),
            filled_qty=float(d.get("cumExecQty", 0)),
            status=d["orderStatus"],
            timestamp=int(d.get("createdTime", 0)) / 1000,
        )

    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        try:
            await self._post(
                "/v5/position/set-leverage",
                {
                    "category": "linear",
                    "symbol": symbol,
                    "buyLeverage": str(leverage),
                    "sellLeverage": str(leverage),
                },
            )
            return True
        except Exception as e:
            logger.warning(f"Set leverage failed: {e}")
            return False
