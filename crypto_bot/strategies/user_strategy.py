"""User-defined strategy: users write their own buy/sell logic."""
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class DropLevel:
    """% 하락 시 시드의 몇 % 투입할지"""
    drop_pct: float      # e.g. 5.0 = 5% 하락
    invest_ratio: float  # e.g. 0.10 = 시드의 10%


@dataclass
class UserStrategyConfig:
    """사용자가 직접 설정하는 전략 파라미터"""
    name: str = "내 전략"

    # ── 매수 조건 ─────────────────────────────────────────────────────────────
    buy_rsi_below: Optional[float] = 35.0        # RSI 이하면 매수
    buy_macd_cross: bool = True                   # MACD 골든크로스 시 매수
    buy_bb_below: bool = True                     # 볼린저 하단 이탈 시 매수
    buy_score_threshold: float = 35.0             # 점수 이상이면 매수
    buy_volume_spike: bool = False                # 거래량 급증 시 매수 조건 추가

    # ── 매도 조건 ─────────────────────────────────────────────────────────────
    sell_rsi_above: Optional[float] = 70.0        # RSI 이상이면 매도
    sell_macd_cross: bool = True                   # MACD 데드크로스 시 매도
    sell_bb_above: bool = False                    # 볼린저 상단 돌파 시 매도
    sell_score_threshold: float = -35.0            # 점수 이하면 매도

    # ── 손익 관리 ─────────────────────────────────────────────────────────────
    stop_loss_pct: float = 3.0        # 3% 손절
    take_profit_pct: float = 5.0      # 5% 익절
    trailing_stop_pct: float = 2.0    # 2% 트레일링 스탑 (0 = 비활성)
    use_trailing_stop: bool = True

    # ── 분할 매수 (DCA) ───────────────────────────────────────────────────────
    # 몇 % 이상 떨어지면 시드의 몇 % 추가 투입
    dca_levels: list[DropLevel] = field(default_factory=lambda: [
        DropLevel(drop_pct=3.0, invest_ratio=0.05),   # 3% 하락 시 시드 5%
        DropLevel(drop_pct=5.0, invest_ratio=0.10),   # 5% 하락 시 시드 10%
        DropLevel(drop_pct=8.0, invest_ratio=0.15),   # 8% 하락 시 시드 15%
        DropLevel(drop_pct=12.0, invest_ratio=0.20),  # 12% 하락 시 시드 20%
    ])
    base_invest_ratio: float = 0.10  # 기본 투자 비율 (시드의 10%)
    max_total_ratio: float = 0.60    # 최대 총 투자 비율 (시드의 60%)

    # ── 시간 조건 ─────────────────────────────────────────────────────────────
    trade_cooldown_sec: int = 300    # 매매 쿨다운 (초)
    interval: str = "15m"           # 분석 타임프레임

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "buy_rsi_below": self.buy_rsi_below,
            "buy_macd_cross": self.buy_macd_cross,
            "buy_bb_below": self.buy_bb_below,
            "buy_score_threshold": self.buy_score_threshold,
            "buy_volume_spike": self.buy_volume_spike,
            "sell_rsi_above": self.sell_rsi_above,
            "sell_macd_cross": self.sell_macd_cross,
            "sell_bb_above": self.sell_bb_above,
            "sell_score_threshold": self.sell_score_threshold,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "trailing_stop_pct": self.trailing_stop_pct,
            "use_trailing_stop": self.use_trailing_stop,
            "dca_levels": [{"drop_pct": d.drop_pct, "invest_ratio": d.invest_ratio} for d in self.dca_levels],
            "base_invest_ratio": self.base_invest_ratio,
            "max_total_ratio": self.max_total_ratio,
            "trade_cooldown_sec": self.trade_cooldown_sec,
            "interval": self.interval,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UserStrategyConfig":
        cfg = cls()
        for k, v in d.items():
            if k == "dca_levels":
                cfg.dca_levels = [DropLevel(l["drop_pct"], l["invest_ratio"]) for l in v]
            elif hasattr(cfg, k):
                setattr(cfg, k, v)
        return cfg


class UserStrategy:
    """User strategy evaluator."""

    def __init__(self, config: UserStrategyConfig):
        self.cfg = config
        self.position: Optional[dict] = None
        self.dca_done_levels: set = set()   # 이미 적용된 DCA 레벨
        self.total_invested_ratio: float = 0.0
        self.last_trade_time: float = 0

    def evaluate_buy(self, indicators: dict, price: float) -> dict:
        cfg = self.cfg
        signals = []
        matched = 0
        total_conditions = 0

        # RSI 조건
        if cfg.buy_rsi_below is not None:
            total_conditions += 1
            rsi = indicators.get("rsi", 50)
            if rsi < cfg.buy_rsi_below:
                matched += 1
                signals.append(f"RSI {rsi:.1f} < {cfg.buy_rsi_below}")

        # MACD 골든크로스
        if cfg.buy_macd_cross:
            total_conditions += 1
            if indicators.get("macd_hist", 0) > 0:
                matched += 1
                signals.append("MACD 골든크로스")

        # 볼린저 하단
        if cfg.buy_bb_below:
            total_conditions += 1
            if price < indicators.get("bb_lower", price + 1):
                matched += 1
                signals.append(f"볼린저 하단({indicators.get('bb_lower', 0):,.0f}) 이탈")

        # 점수
        total_conditions += 1
        score = indicators.get("score", 0)
        if score >= cfg.buy_score_threshold:
            matched += 1
            signals.append(f"매매점수 {score:.0f} >= {cfg.buy_score_threshold}")

        # 거래량 급증
        if cfg.buy_volume_spike:
            total_conditions += 1
            if indicators.get("volume_ratio", 1) >= 2.0:
                matched += 1
                signals.append(f"거래량 급증 {indicators.get('volume_ratio', 0):.1f}x")

        should_buy = matched >= max(1, total_conditions // 2)
        return {"should_buy": should_buy, "signals": signals, "score": score}

    def evaluate_sell(self, indicators: dict, price: float, entry_price: float) -> dict:
        cfg = self.cfg
        signals = []
        pnl_pct = (price - entry_price) / entry_price * 100

        # 손절
        if pnl_pct <= -cfg.stop_loss_pct:
            return {"should_sell": True, "signals": [f"손절 {pnl_pct:.1f}%"], "reason": "stop_loss"}

        # 익절
        if pnl_pct >= cfg.take_profit_pct:
            return {"should_sell": True, "signals": [f"익절 {pnl_pct:.1f}%"], "reason": "take_profit"}

        # 트레일링 스탑
        if cfg.use_trailing_stop and self.position:
            high = self.position.get("high_price", entry_price)
            if price > high:
                self.position["high_price"] = price
            trail_pct = (high - price) / high * 100
            if trail_pct >= cfg.trailing_stop_pct:
                return {
                    "should_sell": True,
                    "signals": [f"트레일링 스탑 (고점 대비 -{trail_pct:.1f}%)"],
                    "reason": "trailing_stop",
                }

        matched = 0
        total_conditions = 0

        # RSI 과매수
        if cfg.sell_rsi_above is not None:
            total_conditions += 1
            rsi = indicators.get("rsi", 50)
            if rsi > cfg.sell_rsi_above:
                matched += 1
                signals.append(f"RSI {rsi:.1f} > {cfg.sell_rsi_above}")

        # MACD 데드크로스
        if cfg.sell_macd_cross:
            total_conditions += 1
            if indicators.get("macd_hist", 0) < 0:
                matched += 1
                signals.append("MACD 데드크로스")

        # 볼린저 상단
        if cfg.sell_bb_above:
            total_conditions += 1
            if price > indicators.get("bb_upper", price - 1):
                matched += 1
                signals.append(f"볼린저 상단({indicators.get('bb_upper', 0):,.0f}) 돌파")

        # 점수
        total_conditions += 1
        score = indicators.get("score", 0)
        if score <= cfg.sell_score_threshold:
            matched += 1
            signals.append(f"매매점수 {score:.0f} <= {cfg.sell_score_threshold}")

        should_sell = total_conditions > 0 and matched >= max(1, total_conditions // 2)
        return {"should_sell": should_sell, "signals": signals, "reason": "signal" if should_sell else ""}

    def calc_dca_amount(self, seed: float, entry_price: float, current_price: float) -> float:
        """DCA: 하락 % 에 따른 추가 투자 금액 계산"""
        drop_pct = (entry_price - current_price) / entry_price * 100
        if drop_pct <= 0:
            return 0.0

        extra_ratio = 0.0
        for level in sorted(self.cfg.dca_levels, key=lambda x: x.drop_pct, reverse=True):
            level_key = level.drop_pct
            if drop_pct >= level.drop_pct and level_key not in self.dca_done_levels:
                # 최대 누적 투자 비율 체크
                if self.total_invested_ratio + level.invest_ratio <= self.cfg.max_total_ratio:
                    extra_ratio = level.invest_ratio
                    self.dca_done_levels.add(level_key)
                    break

        return seed * extra_ratio

    def reset_position(self):
        self.position = None
        self.dca_done_levels.clear()
        self.total_invested_ratio = 0.0
