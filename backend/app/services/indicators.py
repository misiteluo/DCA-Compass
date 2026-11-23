"""Pure indicator math on plain lists. Every function is look-ahead free:
the value at index i only uses data up to i."""
from __future__ import annotations

import math
import statistics


def sma(values: list[float], n: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    s = 0.0
    for i, v in enumerate(values):
        s += v
        if i >= n:
            s -= values[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def ema(values: list[float], n: int) -> list[float]:
    k = 2 / (n + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(out[-1] + k * (v - out[-1]))
    return out


def rsi(closes: list[float], n: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    gains = [max(closes[i] - closes[i - 1], 0.0) for i in range(1, len(closes))]
    losses = [max(closes[i - 1] - closes[i], 0.0) for i in range(1, len(closes))]
    for i in range(n, len(gains) + 1):
        g = statistics.fmean(gains[i - n : i])
        loss = statistics.fmean(losses[i - n : i])
        out[i] = 100.0 if loss == 0 else 100 - 100 / (1 + g / loss)
    return out


def macd_hist_pct(closes: list[float]) -> list[float]:
    """MACD histogram divided by price (%), so assets are comparable."""
    fast, slow = ema(closes, 12), ema(closes, 26)
    line = [f - s for f, s in zip(fast, slow)]
    signal = ema(line, 9)
    return [(l - s) / p * 100 if p else 0.0 for l, s, p in zip(line, signal, closes)]


def bollinger_pct_b(closes: list[float], n: int = 20) -> list[float | None]:
    mid = sma(closes, n)
    out: list[float | None] = [None] * len(closes)
    for i in range(n - 1, len(closes)):
        sd = statistics.pstdev(closes[i - n + 1 : i + 1])
        if sd == 0:
            out[i] = 0.5
        else:
            out[i] = (closes[i] - (mid[i] - 2 * sd)) / (4 * sd)
    return out


def rolling_vol(returns: list[float], n: int = 20) -> list[float | None]:
    out: list[float | None] = [None] * len(returns)
    for i in range(n - 1, len(returns)):
        out[i] = statistics.pstdev(returns[i - n + 1 : i + 1]) * math.sqrt(252) * 100
    return out


def daily_returns(closes: list[float]) -> list[float]:
    return [0.0] + [(closes[i] / closes[i - 1] - 1) for i in range(1, len(closes))]


def percentile_score(series: list[float], *, low_is_high: bool) -> float | None:
    """Score the last value of a series by its percentile rank (0-100).

    low_is_high=True: a low current value means cheap/opportunity → high score.
    """
    vals = [v for v in series if v is not None]
    if len(vals) < 30:
        return None
    cur = vals[-1]
    rank = sum(1 for v in vals if v <= cur) / len(vals) * 100
    return round(100 - rank if low_is_high else rank, 1)


def max_drawdown(values: list[float]) -> float:
    """Worst peak-to-trough decline in % (negative or 0)."""
    peak, worst = -math.inf, 0.0
    for v in values:
        peak = max(peak, v)
        if peak > 0:
            worst = min(worst, (v / peak - 1) * 100)
    return round(worst, 2)
