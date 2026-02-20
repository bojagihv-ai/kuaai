"""Upbit exchange connector (KRW spot market)."""
import hashlib
import uuid
import asyncio
import logging
from typing import Optional
from urllib.parse import urlencode

import aiohttp
import jwt

from .base import BaseExchange, Ticker, OrderBook, Balance, Order, FundingRate

logger = logging.getLogger(__name__)

UPBIT_BASE = "https://api.upbit.com/v1"


class UpbitExchange(BaseExchange):
    name = "upbit"
    taker_fee = 0.0005   # 0.05%
    maker_fee = 0.0005

    # ── Internal helpers ─────────────────────────────────────────────────────
    def _auth_header(self, query_params: dict = None) -> dict:
        payload = {"access_key": self.api_key, "nonce": str(uuid.uuid4())}
        if query_params:
            query_string = urlencode(query_params).encode()
            m = hashlib.sha512()
            m.update(query_string)
            payload["query_hash"] = m.hexdigest()
            payload["query_hash_alg"] = "SHA512"
        token = jwt.encode(payload, self.secret, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    async def _get(self, path: str, params: dict = None, auth: bool = False):
        headers = self._auth_header(params) if auth else {}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{UPBIT_BASE}{path}", params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def _post(self, path: str, data: dict):
        headers = self._auth_header(data)
        headers["Content-Type"] = "application/json"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{UPBIT_BASE}{path}", json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def _delete(self, path: str, params: dict):
        headers = self._auth_header(params)
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{UPBIT_BASE}{path}", params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    # ── Market data ──────────────────────────────────────────────────────────
    async def get_ticker(self, symbol: str = "KRW-BTC") -> Ticker:
        data = await self._get("/ticker", {"markets": symbol})
        d = data[0]
        return Ticker(
            symbol=symbol,
            price=d["trade_price"],
            volume_24h=d["acc_trade_volume_24h"],
            change_24h=d["signed_change_rate"] * 100,
            timestamp=d["timestamp"] / 1000,
        )

    async def get_orderbook(self, symbol: str = "KRW-BTC", depth: int = 10) -> OrderBook:
        data = await self._get("/orderbook", {"markets": symbol})
        ob = data[0]
        units = ob["orderbook_units"][:depth]
        bids = [[u["bid_price"], u["bid_size"]] for u in units]
        asks = [[u["ask_price"], u["ask_size"]] for u in units]
        return OrderBook(bids=bids, asks=asks, timestamp=ob["timestamp"] / 1000)

    async def get_ohlcv(self, symbol: str = "KRW-BTC", interval: str = "1m", limit: int = 200) -> list:
        interval_map = {
            "1m": ("minutes/1", {}),
            "3m": ("minutes/3", {}),
            "5m": ("minutes/5", {}),
            "15m": ("minutes/15", {}),
            "30m": ("minutes/30", {}),
            "1h": ("minutes/60", {}),
            "4h": ("minutes/240", {}),
            "1d": ("days", {}),
            "1w": ("weeks", {}),
        }
        path_suffix, extra = interval_map.get(interval, ("minutes/1", {}))
        params = {"market": symbol, "count": min(limit, 200), **extra}
        data = await self._get(f"/candles/{path_suffix}", params)
        # Upbit returns newest-first; reverse to oldest-first
        data = list(reversed(data))
        return [
            [
                int(d["candle_date_time_utc"].replace("T", " ").replace("-", "").replace(":", "").replace(" ", "")),
                d["opening_price"],
                d["high_price"],
                d["low_price"],
                d["trade_price"],
                d["candle_acc_trade_volume"],
            ]
            for d in data
        ]

    async def get_all_markets(self) -> list[str]:
        data = await self._get("/market/all", {"isDetails": "false"})
        return [m["market"] for m in data if m["market"].startswith("KRW-")]

    # ── Account ───────────────────────────────────────────────────────────────
    async def get_balances(self) -> list[Balance]:
        data = await self._get("/accounts", auth=True)
        return [
            Balance(
                currency=d["currency"],
                available=float(d["balance"]),
                locked=float(d["locked"]),
            )
            for d in data
        ]

    async def get_krw_balance(self) -> float:
        balances = await self.get_balances()
        for b in balances:
            if b.currency == "KRW":
                return b.available
        return 0.0

    # ── Trading ───────────────────────────────────────────────────────────────
    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str = "market",
        qty: float = None,
        price: Optional[float] = None,
        krw_amount: Optional[float] = None,
    ) -> Order:
        data: dict = {"market": symbol, "side": side}

        if order_type == "market":
            data["ord_type"] = "price" if side == "bid" else "market"
            if side == "bid":
                # Upbit 매수는 KRW 금액으로
                data["price"] = str(krw_amount or (qty * price))
            else:
                data["volume"] = str(qty)
        else:
            data["ord_type"] = "limit"
            data["price"] = str(price)
            data["volume"] = str(qty)

        resp = await self._post("/orders", data)
        return self._parse_order(resp)

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        try:
            await self._delete("/order", {"uuid": order_id})
            return True
        except Exception:
            return False

    async def get_order(self, symbol: str, order_id: str) -> Order:
        data = await self._get("/order", {"uuid": order_id}, auth=True)
        return self._parse_order(data)

    def _parse_order(self, d: dict) -> Order:
        return Order(
            order_id=d.get("uuid", ""),
            symbol=d.get("market", ""),
            side="buy" if d.get("side") == "bid" else "sell",
            order_type=d.get("ord_type", ""),
            price=float(d.get("price") or 0),
            qty=float(d.get("volume") or 0),
            filled_qty=float(d.get("executed_volume") or 0),
            status=d.get("state", ""),
            timestamp=0,
        )
