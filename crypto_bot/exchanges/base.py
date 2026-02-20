"""Base exchange class - all exchanges inherit from this."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import time


@dataclass
class OrderBook:
    bids: list  # [[price, qty], ...]
    asks: list
    timestamp: float


@dataclass
class Ticker:
    symbol: str
    price: float
    volume_24h: float
    change_24h: float
    timestamp: float


@dataclass
class Balance:
    currency: str
    available: float
    locked: float

    @property
    def total(self):
        return self.available + self.locked


@dataclass
class Order:
    order_id: str
    symbol: str
    side: str        # 'buy' | 'sell'
    order_type: str  # 'limit' | 'market'
    price: float
    qty: float
    filled_qty: float
    status: str      # 'open' | 'filled' | 'cancelled'
    timestamp: float


@dataclass
class FundingRate:
    symbol: str
    rate: float       # e.g. 0.0001 = 0.01%
    next_funding: float  # unix timestamp


class BaseExchange(ABC):
    name: str = "base"
    taker_fee: float = 0.0
    maker_fee: float = 0.0

    def __init__(self, api_key: str = "", secret: str = "", passphrase: str = ""):
        self.api_key = api_key
        self.secret = secret
        self.passphrase = passphrase

    # ── Market data ──────────────────────────────────────────────────────────
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        ...

    @abstractmethod
    async def get_orderbook(self, symbol: str, depth: int = 10) -> OrderBook:
        ...

    @abstractmethod
    async def get_ohlcv(self, symbol: str, interval: str = "1m", limit: int = 200) -> list:
        """Return list of [timestamp, open, high, low, close, volume]"""
        ...

    # ── Account ───────────────────────────────────────────────────────────────
    @abstractmethod
    async def get_balances(self) -> list[Balance]:
        ...

    # ── Trading ───────────────────────────────────────────────────────────────
    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        qty: float,
        price: Optional[float] = None,
    ) -> Order:
        ...

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        ...

    @abstractmethod
    async def get_order(self, symbol: str, order_id: str) -> Order:
        ...

    # ── Futures (optional) ────────────────────────────────────────────────────
    async def get_funding_rate(self, symbol: str) -> Optional[FundingRate]:
        return None

    # ── Fee helpers ───────────────────────────────────────────────────────────
    def calc_fee(self, amount: float, is_taker: bool = True) -> float:
        fee_rate = self.taker_fee if is_taker else self.maker_fee
        return amount * fee_rate

    def _ts(self) -> int:
        return int(time.time() * 1000)
