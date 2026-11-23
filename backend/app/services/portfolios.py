"""Lazy portfolios: canonical allocations, quarterly-rebalanced backtests
from Yahoo ETF prices (2017+). Allocations are the widely published ones;
where a portfolio has several variants, the tickers used are listed here."""
from __future__ import annotations

import math
import statistics
from datetime import date

from app.services import indicators as ind
from app.services.providers import yahoo

PORTFOLIOS = [
    {"id": "all-weather", "name": "达里奥全天候组合", "risk": "低",
     "allocation": {"VTI": 30, "TLT": 40, "IEF": 15, "GLD": 7.5, "DBC": 7.5},
     "rebalance": "季度再平衡", "suitable": "保守型与退休人群",
     "note": "按风险平价思想分散到股、长债、中债、黄金与商品。"},
    {"id": "permanent", "name": "永久组合", "risk": "低",
     "allocation": {"SPY": 25, "TLT": 25, "GLD": 25, "SHV": 25},
     "rebalance": "年度再平衡（偏离 35/15 时触发）", "suitable": "极度厌恶波动的长期资金",
     "note": "股、长债、黄金、现金四等分，应对四种经济环境。"},
    {"id": "sixty-forty", "name": "经典 60/40 股债组合", "risk": "中",
     "allocation": {"SPY": 60, "AGG": 40},
     "rebalance": "季度再平衡", "suitable": "大多数长期投资者",
     "note": "最经典的股债平衡基准组合。"},
    {"id": "yale", "name": "耶鲁大学捐赠基金组合", "risk": "中",
     "allocation": {"VTI": 30, "EFA": 20, "VNQ": 15, "TLT": 15, "TIP": 10, "DBC": 10},
     "rebalance": "季度再平衡", "suitable": "能承受另类资产波动的长期投资者",
     "note": "斯文森在耶鲁的分散化思路的 ETF 近似实现。"},
    {"id": "ivy", "name": "常春藤组合 (Meb Faber)", "risk": "中",
     "allocation": {"VTI": 20, "EFA": 20, "VNQ": 20, "DBC": 20, "AGG": 20},
     "rebalance": "季度再平衡", "suitable": "追求跨资产类别均衡的投资者",
     "note": "五大资产类别等权：美股、国际股、地产、商品、债券。"},
    {"id": "coffeehouse", "name": "咖啡罐组合 (Schultheis)", "risk": "中",
     "allocation": {"SPY": 10, "VO": 10, "IWM": 10, "IWN": 10, "EFA": 10, "VNQ": 10, "AGG": 40},
     "rebalance": "年度再平衡", "suitable": "想细分美股风格的长期投资者",
     "note": "六个股票风格切片各 10% + 40% 债券（此处合并为 AGG）。"},
    {"id": "three-fund", "name": "懒人三基金组合 (Bernstein)", "risk": "中",
     "allocation": {"VTI": 34, "VXUS": 33, "BND": 33},
     "rebalance": "季度再平衡", "suitable": "想用最少基金覆盖全球的投资者",
     "note": "全美股市 + 全国际股市 + 全债券市场，三只基金走天下。"},
    {"id": "core-four", "name": "核心四资产组合 (Ferri)", "risk": "中",
     "allocation": {"VTI": 36, "VXUS": 18, "VNQ": 6, "BND": 40},
     "rebalance": "季度再平衡", "suitable": "在三基金基础上想要地产倾斜的投资者",
     "note": "三基金 + 6% REITs 的核心四资产版本。"},
    {"id": "buffett", "name": "巴菲特组合 (90/10)", "risk": "高",
     "allocation": {"SPY": 90, "BIL": 10},
     "rebalance": "年度再平衡", "suitable": "年轻、期限长、能承受大回撤的投资者",
     "note": "90% 标普500 + 10% 短期国债，源自巴菲特给妻子的遗嘱安排。"},
    {"id": "swensen", "name": "斯文森懒人组合", "risk": "中",
     "allocation": {"VTI": 30, "EFA": 15, "EEM": 5, "VNQ": 20, "IEF": 15, "TIP": 15},
     "rebalance": "季度再平衡", "suitable": "个人投资者的捐赠基金式配置",
     "note": "斯文森在《非凡的成功》里给个人投资者的六资产方案。"},
]


def backtest_portfolio(spec: dict, price_map: dict[str, list[dict]]) -> dict:
    tickers = list(spec["allocation"])
    series = {t: {r["date"]: r["close"] for r in price_map.get(t, [])} for t in tickers}
    common = sorted(set.intersection(*[set(s) for s in series.values()])) if series else []
    common = [d for d in common if d >= "2017-01-01"]
    if len(common) < 60:
        return {"id": spec["id"], "status": "unavailable"}
    weekly = common[::5]
    shares = {t: 0.0 for t in tickers}
    value_curve: list[tuple[str, float]] = []
    start_value = 10_000.0
    for t, w in spec["allocation"].items():
        shares[t] = start_value * w / 100 / series[t][weekly[0]]
    last_quarter = None
    for d in weekly:
        q = (int(d[:4]), (int(d[5:7]) - 1) // 3)
        total = sum(shares[t] * series[t][d] for t in tickers)
        if last_quarter is not None and q != last_quarter:  # quarterly rebalance
            for t, w in spec["allocation"].items():
                shares[t] = total * w / 100 / series[t][d]
            total = sum(shares[t] * series[t][d] for t in tickers)
        last_quarter = q
        value_curve.append((d, total))
    vals = [v for _, v in value_curve]
    years = (date.fromisoformat(weekly[-1]) - date.fromisoformat(weekly[0])).days / 365.25
    wrets = [vals[i] / vals[i - 1] - 1 for i in range(1, len(vals))]
    sd = statistics.pstdev(wrets) if len(wrets) > 1 else 0.0
    mean = statistics.fmean(wrets) if wrets else 0.0
    yearly: dict[str, float] = {}
    prev = start_value
    seen: dict[str, float] = {}
    for d, v in value_curve:
        seen[d[:4]] = v
    last = start_value
    for y in sorted(seen):
        yearly[y] = round((seen[y] / last - 1) * 100, 2)
        last = seen[y]
    return {
        "id": spec["id"], "name": spec["name"], "risk": spec["risk"],
        "allocation": spec["allocation"], "rebalance": spec["rebalance"],
        "suitable": spec["suitable"], "note": spec["note"], "status": "ok",
        "period": f"{weekly[0]} ~ {weekly[-1]}", "initial": start_value,
        "final_value": round(vals[-1], 2),
        "annualized_pct": round(((vals[-1] / start_value) ** (1 / years) - 1) * 100, 2),
        "volatility_pct": round(sd * math.sqrt(52) * 100, 2),
        "max_drawdown_pct": ind.max_drawdown(vals),
        "sharpe": round(mean / sd * math.sqrt(52), 2) if sd else 0.0,
        "yearly": yearly,
    }


def build_portfolios() -> list[dict]:
    tickers = sorted({t for p in PORTFOLIOS for t in p["allocation"]})
    price_map = {t: yahoo.fetch_series(t, "2016-06-01") for t in tickers}
    return [backtest_portfolio(p, price_map) for p in PORTFOLIOS]
