"""Technical indicators - pure numpy, no TA-Lib dependency required."""
import numpy as np
from dataclasses import dataclass
from typing import Optional


def _ema(values: np.ndarray, period: int) -> np.ndarray:
    k = 2 / (period + 1)
    ema = np.zeros_like(values)
    ema[0] = values[0]
    for i in range(1, len(values)):
        ema[i] = values[i] * k + ema[i - 1] * (1 - k)
    return ema


def _sma(values: np.ndarray, period: int) -> np.ndarray:
    return np.convolve(values, np.ones(period) / period, mode="full")[: len(values)]


@dataclass
class IndicatorResult:
    rsi: float
    macd: float
    macd_signal: float
    macd_hist: float
    bb_upper: float
    bb_mid: float
    bb_lower: float
    ema5: float
    ema20: float
    ema60: float
    ema120: float
    volume_ratio: float     # current vol / 20-period avg vol
    stoch_k: float
    stoch_d: float
    atr: float
    # Derived signals
    trend: str              # 'strong_up' | 'up' | 'sideways' | 'down' | 'strong_down'
    signal: str             # 'buy' | 'sell' | 'hold'
    score: float            # -100 ~ +100


def compute_indicators(ohlcv: list) -> Optional[IndicatorResult]:
    """ohlcv: list of [ts, open, high, low, close, volume]"""
    if len(ohlcv) < 60:
        return None

    arr = np.array(ohlcv, dtype=float)
    closes = arr[:, 4]
    highs = arr[:, 2]
    lows = arr[:, 3]
    volumes = arr[:, 5]

    # ── RSI (14) ──────────────────────────────────────────────────────────────
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-14:])
    avg_loss = np.mean(losses[-14:])
    rs = avg_gain / avg_loss if avg_loss != 0 else 100
    rsi = 100 - 100 / (1 + rs)

    # ── MACD (12, 26, 9) ─────────────────────────────────────────────────────
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd_line = ema12 - ema26
    signal_line = _ema(macd_line, 9)
    macd_hist = macd_line[-1] - signal_line[-1]

    # ── Bollinger Bands (20, 2σ) ─────────────────────────────────────────────
    sma20 = np.mean(closes[-20:])
    std20 = np.std(closes[-20:])
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20

    # ── EMAs ─────────────────────────────────────────────────────────────────
    ema5_val = _ema(closes, 5)[-1]
    ema20_val = _ema(closes, 20)[-1]
    ema60_val = _ema(closes, 60)[-1] if len(closes) >= 60 else closes[-1]
    ema120_val = _ema(closes, 120)[-1] if len(closes) >= 120 else closes[-1]

    # ── Volume ratio ─────────────────────────────────────────────────────────
    vol_avg = np.mean(volumes[-20:])
    vol_ratio = volumes[-1] / vol_avg if vol_avg > 0 else 1.0

    # ── Stochastic (14, 3) ────────────────────────────────────────────────────
    period_high = np.max(highs[-14:])
    period_low = np.min(lows[-14:])
    stoch_k = (closes[-1] - period_low) / (period_high - period_low) * 100 if period_high != period_low else 50
    # D = 3-period SMA of K (simplified: use last 3 raw K values)
    ks = []
    for i in range(3):
        idx = -(i + 1)
        ph = np.max(highs[max(-14 + idx, -len(highs)): idx if idx != 0 else len(highs)])
        pl = np.min(lows[max(-14 + idx, -len(lows)): idx if idx != 0 else len(lows)])
        ks.append((closes[idx] - pl) / (ph - pl) * 100 if ph != pl else 50)
    stoch_d = np.mean(ks)

    # ── ATR (14) ─────────────────────────────────────────────────────────────
    trs = []
    for i in range(-14, 0):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    atr = np.mean(trs)

    # ── Signal scoring ────────────────────────────────────────────────────────
    score = 0.0
    price = closes[-1]

    # RSI (weight 25)
    if rsi < 30:
        score += 25
    elif rsi < 40:
        score += 12
    elif rsi > 70:
        score -= 25
    elif rsi > 60:
        score -= 12

    # MACD (weight 20)
    if macd_hist > 0 and macd_line[-1] > signal_line[-1]:
        score += 20
    elif macd_hist < 0 and macd_line[-1] < signal_line[-1]:
        score -= 20

    # Bollinger Bands (weight 15)
    if price < bb_lower:
        score += 15
    elif price > bb_upper:
        score -= 15
    else:
        bb_pct = (price - bb_lower) / (bb_upper - bb_lower)
        score += (0.5 - bb_pct) * 20

    # EMA trend (weight 20)
    if ema5_val > ema20_val > ema60_val:
        score += 20
    elif ema5_val > ema20_val:
        score += 10
    elif ema5_val < ema20_val < ema60_val:
        score -= 20
    elif ema5_val < ema20_val:
        score -= 10

    # Stochastic (weight 10)
    if stoch_k < 20 and stoch_d < 20:
        score += 10
    elif stoch_k > 80 and stoch_d > 80:
        score -= 10

    # Volume confirmation (weight 10)
    if vol_ratio > 1.5:
        score += 10 if score > 0 else -10

    # ── Trend ─────────────────────────────────────────────────────────────────
    if score >= 50:
        trend = "strong_up"
    elif score >= 20:
        trend = "up"
    elif score <= -50:
        trend = "strong_down"
    elif score <= -20:
        trend = "down"
    else:
        trend = "sideways"

    # ── Signal ────────────────────────────────────────────────────────────────
    if score >= 40:
        signal = "buy"
    elif score <= -40:
        signal = "sell"
    else:
        signal = "hold"

    return IndicatorResult(
        rsi=round(rsi, 2),
        macd=round(float(macd_line[-1]), 6),
        macd_signal=round(float(signal_line[-1]), 6),
        macd_hist=round(macd_hist, 6),
        bb_upper=round(bb_upper, 2),
        bb_mid=round(sma20, 2),
        bb_lower=round(bb_lower, 2),
        ema5=round(ema5_val, 2),
        ema20=round(ema20_val, 2),
        ema60=round(ema60_val, 2),
        ema120=round(ema120_val, 2),
        volume_ratio=round(vol_ratio, 2),
        stoch_k=round(stoch_k, 2),
        stoch_d=round(stoch_d, 2),
        atr=round(atr, 2),
        trend=trend,
        signal=signal,
        score=round(score, 2),
    )
