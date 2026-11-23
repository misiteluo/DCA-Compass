"""Weekly-DCA backtest, strictly no look-ahead.

Historical scores for the backtest are a price-derived percentile composite
(8 generic dimensions, expanding-window percentiles — the value on day t only
uses data up to t), mapped through the asset's own multiplier function.
"""
from __future__ import annotations

import bisect
import math
import statistics
from datetime import date

from app.core.config import WEEKLY_BASE
from app.services import indicators as ind
from app.services.scoring import multiplier

STRESS_WINDOWS = {
    "btc": [("2018 熊市", "2018-01-01", "2018-12-31"), ("2020 COVID 暴跌", "2020-02-15", "2020-03-31"),
            ("2021 监管风暴", "2021-05-01", "2021-07-31"), ("2022 加息 + FTX", "2022-01-01", "2022-12-31"),
            ("2025 回调", "2025-01-01", "2025-12-31")],
    "gold": [("2018 加息周期", "2018-01-01", "2018-12-31"), ("2020 COVID", "2020-02-15", "2020-08-31"),
             ("2022 实际利率冲高", "2022-01-01", "2022-10-31"), ("2025 高位震荡", "2025-01-01", "2025-12-31")],
    "nasdaq": [("2020 COVID", "2020-02-15", "2020-03-31"), ("2022 加息熊市", "2022-01-01", "2022-12-31"),
               ("2024 地缘冲突", "2024-01-01", "2024-12-31"), ("2025 关税冲击", "2025-01-01", "2025-12-31")],
    "sp500": [("2018 贸易战", "2018-01-01", "2018-12-31"), ("2020 COVID", "2020-02-15", "2020-03-31"),
              ("2022 加息熊市", "2022-01-01", "2022-12-31"), ("2023 银行业危机", "2023-03-01", "2023-05-31")],
    "hs300": [("2015 股灾", "2015-06-15", "2015-09-30"), ("2018 贸易战", "2018-01-01", "2018-12-31"),
              ("2020 COVID", "2020-01-15", "2020-03-31"), ("2022 俄乌冲突", "2022-02-24", "2022-12-31")],
}


def _score_series(closes: list[float]) -> dict[int, float]:
    """Expanding-window percentile composite at weekly indices."""
    ma200, ma50 = ind.sma(closes, 200), ind.sma(closes, 50)
    rets = ind.daily_returns(closes)
    series = {
        "ma200": [((c / m - 1) * 100 if m else None) for c, m in zip(closes, ma200)],
        "ma50": [((c / m - 1) * 100 if m else None) for c, m in zip(closes, ma50)],
        "rsi": ind.rsi(closes),
        "boll": ind.bollinger_pct_b(closes),
        "macd": ind.macd_hist_pct(closes),
        "vol": ind.rolling_vol(rets),
        "dd": [((c / max(closes[max(0, i - 251): i + 1]) - 1) * 100) for i, c in enumerate(closes)],
        "pos": [((c - min(closes[max(0, i - 755): i + 1])) /
                 max(max(closes[max(0, i - 755): i + 1]) - min(closes[max(0, i - 755): i + 1]),
                     1e-9) * 100) for i, c in enumerate(closes)],
    }
    low_high = {"vol": False}  # everything else: low value = high score
    sorted_vals: dict[str, list[float]] = {k: [] for k in series}
    scores: dict[int, float] = {}
    for i in range(len(closes)):
        parts = []
        for k, s in series.items():
            v = s[i]
            if v is None:
                continue
            lst = sorted_vals[k]
            bisect.insort(lst, v)
            if len(lst) >= 60:
                rank = bisect.bisect_right(lst, v) / len(lst) * 100
                parts.append(rank if k in low_high and not low_high[k] else 100 - rank)
        if i % 5 == 0 and i >= 250 and parts:
            scores[i] = round(statistics.fmean(parts), 1)
    return scores


def _cagr(final: float, invested: float, years: float) -> float:
    if invested <= 0 or years <= 0 or final <= 0:
        return 0.0
    return round(((final / invested) ** (1 / years) - 1) * 100, 2)


def run_backtest(asset_id: str, prices: list[dict]) -> dict:
    closes = [r["close"] for r in prices]
    dates = [r["date"] for r in prices]
    scores = _score_series(closes)
    weekly_idx = sorted(scores)
    if not weekly_idx:
        return {}
    years = (date.fromisoformat(dates[weekly_idx[-1]]) -
             date.fromisoformat(dates[weekly_idx[0]])).days / 365.25

    strat_shares = reg_shares = 0.0
    strat_in = reg_in = 0.0
    curve = []
    yearly: dict[int, dict] = {}
    for i in weekly_idx:
        p, m = closes[i], multiplier(asset_id, scores[i])
        strat_shares += WEEKLY_BASE * m / p
        reg_shares += WEEKLY_BASE / p
        strat_in += WEEKLY_BASE * m
        reg_in += WEEKLY_BASE
        y = int(dates[i][:4])
        yr = yearly.setdefault(y, {"start": curve[-1]["strategy"] if curve else 0.0,
                                   "contrib": 0.0, "contrib_reg": 0.0})
        yr["contrib"] += WEEKLY_BASE * m
        yr["contrib_reg"] += WEEKLY_BASE
        yr["end"] = strat_shares * p
        yr["end_reg"] = reg_shares * p
        curve.append({"date": dates[i], "strategy": round(strat_shares * p, 2),
                      "regular": round(reg_shares * p, 2)})
    total_weeks = len(weekly_idx)
    bh_shares = (WEEKLY_BASE * total_weeks) / closes[weekly_idx[0]]
    for c in curve:
        pass
    bh_curve = {c["date"]: round(bh_shares * closes[dates.index(c["date"])], 2) for c in curve[:: max(1, len(curve) // 60)]}
    for c in curve:
        c["buyhold"] = round(bh_shares * closes[dates.index(c["date"])], 2)

    def strat_summary(shares, invested):
        final = shares * closes[-1]
        return {"invested": round(invested, 2), "final_value": round(final, 2),
                "total_return_pct": round((final / invested - 1) * 100, 2) if invested else 0.0,
                "cagr_pct": _cagr(final, invested, years)}

    strat = strat_summary(strat_shares, strat_in)
    reg = strat_summary(reg_shares, reg_in)
    bh_final = bh_shares * closes[-1]
    bh = {"invested": round(WEEKLY_BASE * total_weeks, 2), "final_value": round(bh_final, 2),
          "total_return_pct": round((bh_final / (WEEKLY_BASE * total_weeks) - 1) * 100, 2),
          "cagr_pct": _cagr(bh_final, WEEKLY_BASE * total_weeks, years)}

    strat_vals = [c["strategy"] for c in curve]
    wrets = [closes[i] / closes[j] - 1 for j, i in zip(weekly_idx, weekly_idx[1:])]
    mean_w = statistics.fmean(wrets) if wrets else 0.0
    sd_w = statistics.pstdev(wrets) if len(wrets) > 1 else 0.0
    downside = [r for r in wrets if r < 0]
    sd_d = statistics.pstdev(downside) if len(downside) > 1 else 0.0
    risk = {
        "max_drawdown_pct": ind.max_drawdown(strat_vals),
        "sharpe": round(mean_w / sd_w * math.sqrt(52), 3) if sd_w else 0.0,
        "sortino": round(mean_w / sd_d * math.sqrt(52), 3) if sd_d else 0.0,
        "volatility_pct": round(sd_w * math.sqrt(52) * 100, 2),
        "note": "夏普/索提诺/波动率基于资产周收益率年化；最大回撤基于策略组合市值曲线",
    }

    yearly_rows = []
    for y in sorted(yearly):
        yr = yearly[y]
        def yret(end, start, contrib):
            base = start + contrib
            return round((end / base - 1) * 100, 2) if base else 0.0
        yearly_rows.append({
            "year": y,
            "strategy_pct": yret(yr["end"], yr["start"], yr["contrib"]),
            "regular_pct": yret(yr["end_reg"], yr["start"], yr["contrib_reg"]),
            "buyhold_pct": None,
        })
    # buy&hold yearly = asset calendar-year return
    by_year_close: dict[int, list[float]] = {}
    for d, c in zip(dates, closes):
        by_year_close.setdefault(int(d[:4]), []).append(c)
    asset_year = {y: round((v[-1] / v[0] - 1) * 100, 2) for y, v in by_year_close.items()}
    for row in yearly_rows:
        row["buyhold_pct"] = asset_year.get(row["year"])

    month_end: dict[str, float] = {}
    for d, c in zip(dates, closes):
        month_end[d[:7]] = c
    mkeys = sorted(month_end)
    monthly: dict[str, list] = {}
    for a, b in zip(mkeys, mkeys[1:]):
        monthly.setdefault(b[:4], [None] * 12)[int(b[5:7]) - 1] = round(
            (month_end[b] / month_end[a] - 1) * 100, 2)

    rolling = []
    for yrs in (1, 3, 5, 10):
        days = int(yrs * 365.25)
        target = date.fromisoformat(dates[-1]).toordinal() - days
        start_c = next((c for d, c in zip(dates, closes)
                        if date.fromisoformat(d).toordinal() >= target), None)
        if start_c:
            rolling.append({"years": yrs,
                            "annualized_pct": round(((closes[-1] / start_c) ** (1 / yrs) - 1) * 100, 2)})

    buckets = {"<-5%": 0, "-5~-2%": 0, "-2~0%": 0, "0~2%": 0, "2~5%": 0, ">5%": 0}
    for r in wrets:
        p = r * 100
        key = ("<-5%" if p < -5 else "-5~-2%" if p < -2 else "-2~0%" if p < 0
               else "0~2%" if p < 2 else "2~5%" if p < 5 else ">5%")
        buckets[key] += 1

    stress = []
    for label, s, e in STRESS_WINDOWS.get(asset_id, []):
        window = [(d, c) for d, c in zip(dates, closes) if s <= d <= e]
        if len(window) > 5:
            stress.append({"label": label, "period": f"{s} ~ {e}",
                           "asset_return_pct": round((window[-1][1] / window[0][1] - 1) * 100, 2),
                           "max_drawdown_pct": ind.max_drawdown([c for _, c in window])})

    step = max(1, len(curve) // 300)
    return {
        "period": f"{dates[weekly_idx[0]]} ~ {dates[-1]}",
        "base_weekly": WEEKLY_BASE,
        "method_note": "周频定投；历史评分由价格派生维度百分位合成（扩张窗口，无未来函数），倍数使用该资产同一映射函数",
        "strategy": strat, "regular": reg, "buyhold": bh,
        "risk": risk, "yearly": yearly_rows, "monthly": monthly,
        "rolling": rolling,
        "distribution": [{"bucket": k, "weeks": v} for k, v in buckets.items()],
        "growth_curve": curve[::step],
        "stress_tests": stress,
        "best_year": max(yearly_rows, key=lambda r: r["strategy_pct"], default=None),
        "worst_year": min(yearly_rows, key=lambda r: r["strategy_pct"], default=None),
    }
