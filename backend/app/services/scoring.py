"""Scoring engine: dimensions → percentile scores → composite → multiplier.

One multiplier function per asset, used by the API display AND the backtest.
If a dimension's data source fails it is returned with score=None and the
remaining weights are renormalized to 100% — data is never fabricated.
"""
from __future__ import annotations

import math
import statistics
from datetime import datetime, timezone

from app.services import indicators as ind

# ---------- multiplier mappings (functional facts from the original) ----------

_PIECEWISE = {
    "btc": [(0, 0.10), (30, 0.30), (50, 0.80), (70, 1.20), (85, 1.95), (100, 3.00)],
    "nasdaq": [(0, 0.0), (50, 0.90), (90, 2.10), (100, 2.50)],
    "sp500": [(0, 0.0), (30, 0.33), (40, 0.60), (70, 1.63), (100, 2.25)],
}


def multiplier(asset_id: str, score: float) -> float:
    """The single mapping function for an asset. Display == backtest."""
    if asset_id == "gold":
        for limit, m in [(30, 0.5), (45, 0.7), (55, 1.0), (70, 1.5), (85, 2.0)]:
            if score < limit:
                return m
        return 3.0
    if asset_id == "hs300":
        return round(min(2.0, max(0.2, 0.2 + (score - 25) * 0.024)), 2)
    pts = _PIECEWISE[asset_id]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if score <= x1:
            return round(y0 + (y1 - y0) * (score - x0) / (x1 - x0), 2)
    return pts[-1][1]


def mapping_table(asset_id: str) -> list[dict]:
    if asset_id == "gold":
        rows = [("<30", 0.5), ("30–44", 0.7), ("45–54", 1.0), ("55–69", 1.5),
                ("70–84", 2.0), ("≥85", 3.0)]
    elif asset_id == "hs300":
        rows = [("0–19", 0.2), ("20–39", 0.3), ("40–59", 0.7), ("60–79", 1.2), ("80–100", 1.7)]
        rows = [(r, multiplier("hs300", {"0–19": 10, "20–39": 30, "40–59": 50,
                                         "60–79": 70, "80–100": 90}[r])) for r, _ in rows]
    else:
        pts = _PIECEWISE[asset_id]
        rows = [(f"{a[0]}–{b[0]}", round((a[1] + b[1]) / 2, 2))
                for a, b in zip(pts, pts[1:])]
    return [{"range": r, "multiplier": m} for r, m in rows]


ZONES = [
    (30, "高估", "减少定投"),
    (50, "偏高估", "降低定投"),
    (70, "合理", "标准定投"),
    (85, "低估", "增加定投"),
    (101, "极度低估", "大幅增加定投"),
]


def zone_of(score: float) -> tuple[str, str]:
    for limit, label, action in ZONES:
        if score < limit:
            return label, action
    return ZONES[-1][1], ZONES[-1][2]


# ---------- price-derived dimension helpers ----------

def _last(series):
    for v in reversed(series):
        if v is not None:
            return v
    return None


def _dim_ma(closes, n, key, name, weight, source):
    ma = ind.sma(closes, n)
    dev = [((c / m - 1) * 100 if m else None) for c, m in zip(closes, ma)]
    score = ind.percentile_score([d for d in dev if d is not None], low_is_high=True)
    return _mk(key, name, weight, _last(dev), "%", score, source,
               f"价格低于 MA{n} 越多，估值分越高")


def _dim_rsi(closes, weight, key="rsi", name="RSI(14)"):
    r = ind.rsi(closes)
    vals = [v for v in r if v is not None]
    return _mk(key, name, weight, _last(r), "", ind.percentile_score(vals, low_is_high=True),
               "Yahoo Finance 价格序列计算", "RSI 越低代表越超卖，机会分越高")


def _dim_macd(closes, weight):
    h = ind.macd_hist_pct(closes)
    return _mk("macd", "MACD", weight, _last(h), "%",
               ind.percentile_score(h[100:], low_is_high=True),
               "Yahoo Finance 价格序列计算", "MACD 柱深度负值代表动量极弱、接近拐点")


def _dim_bollinger(closes, weight):
    b = ind.bollinger_pct_b(closes)
    vals = [v for v in b if v is not None]
    return _mk("bollinger", "布林带 %B", weight, _last(b), "",
               ind.percentile_score(vals, low_is_high=True),
               "Yahoo Finance 价格序列计算", "%B 越低越接近布林带下轨")


def _dim_vol(closes, weight, name="波动率"):
    rets = ind.daily_returns(closes)
    v = ind.rolling_vol(rets)
    vals = [x for x in v if x is not None]
    return _mk("volatility", name, weight, _last(v), "%",
               ind.percentile_score(vals, low_is_high=False),
               "Yahoo Finance 价格序列计算", "波动率处于历史高位往往对应恐慌阶段")


def _dim_drawdown(closes, weight, name="距52周高点回撤"):
    out = []
    for i, c in enumerate(closes):
        hi = max(closes[max(0, i - 251) : i + 1])
        out.append((c / hi - 1) * 100 if hi else 0.0)
    return _mk("drawdown", name, weight, out[-1], "%",
               ind.percentile_score(out, low_is_high=True),
               "Yahoo Finance 价格序列计算", "回撤越深，价格相对高点越便宜")


def _dim_ext(values: list[float], key, name, weight, raw_unit, low_is_high, source, note):
    """Dimension scored from an external level series (VIX, DXY, yields...)."""
    if len(values) < 30:
        return _unavailable(key, name, weight, source, note)
    return _mk(key, name, weight, values[-1], raw_unit,
               ind.percentile_score(values, low_is_high=low_is_high), source, note)


def _mk(key, name, weight, value, unit, score, source, note):
    return {
        "key": key, "name": name, "weight": weight,
        "value": round(value, 2) if isinstance(value, (int, float)) else value,
        "unit": unit, "score": score,
        "status": "ok" if score is not None else "unavailable",
        "source": source, "note": note,
    }


def _unavailable(key, name, weight, source, note, value=None):
    return {"key": key, "name": name, "weight": weight, "value": value, "unit": "",
            "score": None, "status": "unavailable", "source": source, "note": note}


# ---------- per-asset dimension sets ----------

def _btc_dims(ctx) -> list[dict]:
    closes, dates = ctx["closes"], ctx["dates"]
    dims = []
    # AHR999-style: (price / 200d avg cost) * (price / exponential growth value)
    ma200 = ind.sma(closes, 200)
    genesis = datetime(2009, 1, 3, tzinfo=timezone.utc)
    ahr = []
    for d, c, m in zip(dates, closes, ma200):
        if not m:
            continue
        days = (datetime.fromisoformat(d).replace(tzinfo=timezone.utc) - genesis).days
        growth = 10 ** (5.84 * math.log10(max(days, 1)) - 17.01)
        ahr.append((c / m) * (c / growth))
    dims.append(_mk("ahr999", "AHR999 九神指数", 20, ahr[-1] if ahr else None, "",
                    ind.percentile_score(ahr, low_is_high=True),
                    "Yahoo Finance 价格 + 指数增长模型", "低于 0.45 为历史抄底区，0.45–1.2 定投区"))
    # MVRV Z-Score from CoinMetrics market/realized cap ratio
    mvrv = [r["value"] for r in ctx.get("mvrv", [])]
    if len(mvrv) > 400:
        z, run = [], []
        for v in mvrv:
            run.append(v)
            if len(run) > 365:
                mu, sd = statistics.fmean(run), statistics.pstdev(run) or 1.0
                z.append((v - mu) / sd)
        dims.append(_mk("mvrv", "MVRV Z-Score", 15, z[-1] if z else None, "",
                        ind.percentile_score(z, low_is_high=True),
                        "CoinMetrics community API (CapMVRVCur)", "Z 值越低，持币者整体浮盈越少"))
    else:
        dims.append(_unavailable("mvrv", "MVRV Z-Score", 15, "CoinMetrics community API",
                                 "链上数据源本次不可达"))
    dims.append(_dim_ma(closes, 200, "ma200", "MA200 偏离度", 15, "Yahoo Finance 价格序列计算"))
    fgi = [r["value"] for r in ctx.get("fgi", [])]
    dims.append(_dim_ext(fgi, "fgi", "恐惧贪婪指数 FGI", 15, "", True,
                         "alternative.me Fear & Greed API", "极度恐惧时往往是定投机会"))
    puell_raw = [r["value"] for r in ctx.get("issuance", [])]
    if len(puell_raw) > 400:
        ma365 = ind.sma(puell_raw, 365)
        puell = [v / m for v, m in zip(puell_raw, ma365) if m]
        dims.append(_mk("puell", "Puell Multiple 矿工收益比", 15, puell[-1], "",
                        ind.percentile_score(puell, low_is_high=True),
                        "CoinMetrics community API (IssTotUSD)", "矿工收入低于年均代表抛压枯竭"))
    else:
        dims.append(_unavailable("puell", "Puell Multiple 矿工收益比", 15,
                                 "CoinMetrics community API", "链上数据源本次不可达"))
    dims.append(_unavailable("reserve_risk", "Reserve Risk 持币风险", 10,
                             "需要 Glassnode 等付费链上数据", "无免费可靠数据源，暂不接入", None))
    hr = [r["value"] for r in ctx.get("hashrate", [])]
    if len(hr) > 200:
        ratio = [a / b if b else None for a, b in zip(ind.sma(hr, 30), ind.sma(hr, 60))]
        ratio = [r for r in ratio if r is not None]
        dims.append(_mk("hash_ribbon", "算力丝带 Hash Ribbon", 10, ratio[-1], "",
                        ind.percentile_score(ratio, low_is_high=True),
                        "CoinMetrics community API (HashRate)", "30日/60日算力比走弱代表矿工投降"))
    else:
        dims.append(_unavailable("hash_ribbon", "算力丝带 Hash Ribbon", 10,
                                 "CoinMetrics community API", "链上数据源本次不可达"))
    return dims


def _gold_dims(ctx) -> list[dict]:
    closes = ctx["closes"]
    dims = [
        _dim_ext(ctx["dxy"], "dxy", "DXY 美元指数", 25, "", True,
                 "Yahoo Finance (DX-Y.NYB)", "美元走弱利好黄金"),
        _tips_dim(ctx),
        _dim_ma(closes, 200, "ma200", "MA200 均线", 18, "Yahoo Finance 价格序列计算"),
        _dim_rsi(closes, 12),
        _dim_ext(ctx["vix"], "vix", "VIX 恐慌指数", 10, "", False,
                 "Yahoo Finance (^VIX)", "恐慌高企时黄金避险需求上升"),
        _dim_macd(closes, 8),
    ]
    # seasonality: current calendar month's historical average return percentile
    monthly: dict[int, list[float]] = {}
    dates, rows = ctx["dates"], ctx["prices"]
    by_month: dict[str, float] = {}
    for r in rows:
        by_month[r["date"][:7]] = r["close"]
    keys = sorted(by_month)
    for a, b in zip(keys, keys[1:]):
        monthly.setdefault(int(b[5:7]), []).append(by_month[b] / by_month[a] - 1)
    if len(monthly) >= 10:
        avgs = {m: statistics.fmean(v) * 100 for m, v in monthly.items()}
        cur_month = int(dates[-1][5:7])
        rank = sorted(avgs.values()).index(avgs[cur_month]) / len(avgs) * 100
        dims.append(_mk("seasonality", "季节性因子", 7, round(avgs[cur_month], 2), "%",
                        round(rank, 1), "Yahoo Finance 历史月度收益统计",
                        "当前月份在历史上的平均表现分位"))
    else:
        dims.append(_unavailable("seasonality", "季节性因子", 7, "历史月度收益统计", "样本不足"))
    return dims


def _tips_dim(ctx):
    tips = [r["value"] for r in ctx.get("tips", [])]
    return _dim_ext(tips, "tips", "TIPS 实际利率", 20, "%", False,
                    "FRED DFII10 (10年期通胀保值国债收益率)", "实际利率下行利好黄金")


def _nasdaq_dims(ctx) -> list[dict]:
    closes = ctx["closes"]
    return [
        _unavailable("pe", "PE 估值", 12, "无免费可靠的纳指100 PE 历史序列", "数据源待接入"),
        _unavailable("pb", "PB 估值", 8, "无免费可靠的纳指100 PB 历史序列", "数据源待接入"),
        _dim_macd(closes, 10),
        _dim_rsi(closes, 8),
        _dim_bollinger(closes, 7),
        _dim_ma(closes, 50, "ma50", "MA50 偏离度", 10, "Yahoo Finance 价格序列计算"),
        _dim_ma(closes, 200, "ma200", "MA200 偏离度", 8, "Yahoo Finance 价格序列计算"),
        _dim_ext(ctx["vix"], "vix", "VIX 恐慌指数", 12, "", False,
                 "Yahoo Finance (^VIX)", "VIX 冲高代表市场恐慌、定投机会"),
        _dim_ext(ctx["tnx"], "tnx", "美债 10Y 收益率", 7, "%", True,
                 "Yahoo Finance (^TNX)", "收益率冲高会压制成长股估值"),
        _dim_ext(ctx["dxy"], "dxy", "美元指数", 6, "", True,
                 "Yahoo Finance (DX-Y.NYB)", "美元走弱利好美股风险偏好"),
        _dim_ext([r["value"] for r in ctx.get("fgi", [])], "fgi", "恐惧贪婪指数", 12, "",
                 True, "alternative.me Fear & Greed API（情绪代理）", "极度恐惧时往往是定投机会"),
        {**_unavailable("aaii", "AAII 投资者情绪", 0, "AAII 官网周度调查（无开放 API）",
                        "待接入，权重 0 不影响综合分"), "weight": 0},
    ]


def _sp500_dims(ctx) -> list[dict]:
    closes = ctx["closes"]
    return [
        _unavailable("pe", "PE 传统估值", 15, "multpl/FRED 无开放的结构化 PE 序列", "数据源待接入"),
        _unavailable("cape", "CAPE 周期估值", 15, "席勒 CAPE 需手工维护的数据文件", "数据源待接入"),
        _buffett_dim(ctx),
        _dim_rsi(closes, 10, key="rsi_momentum", name="RSI 技术动量"),
        _dim_ext(ctx["vix"], "fgi", "FGI 市场情绪（VIX 代理）", 10, "", False,
                 "Yahoo Finance (^VIX) 换算的情绪分位", "恐慌高企时情绪分高"),
        _unavailable("roe", "ROE 盈利质量", 10, "成分股财报聚合无免费 API", "数据源待接入"),
        _dim_ext(ctx["tnx"], "yld", "宏观环境（美债10Y）", 10, "%", True,
                 "Yahoo Finance (^TNX)", "利率冲高会压制估值"),
        _unavailable("etf_flow", "ETF 资金流向", 10, "资金流数据无免费开放 API", "数据源待接入"),
        _unavailable("pmi", "PMI 经济领先指标", 5, "ISM PMI 为付费发布", "数据源待接入"),
        _unavailable("gpr", "GPR 地缘风险", 5, "地缘风险指数无稳定免费接口", "数据源待接入"),
    ]


def _buffett_dim(ctx):
    will = [r["value"] for r in ctx.get("will5000", [])]
    gdp = [r["value"] for r in ctx.get("gdp", [])]
    if len(will) > 30 and len(gdp) > 30:
        ratio = will[-1] / gdp[-1] * 100
        return _mk("buffett", "巴菲特指标（市值/GDP）", 10, round(ratio, 1), "%", None,
                   "FRED WILL5000INDFC / GDP", "比值已取到，但历史对齐序列不足以算分位")
    return _unavailable("buffett", "巴菲特指标（市值/GDP）", 10,
                        "FRED WILL5000INDFC / GDP", "FRED 本次不可达")


def _hs300_dims(ctx) -> list[dict]:
    closes = ctx["closes"]
    trend = _dim_ma(closes, 60, "trend", "趋势（MA60/MACD/RSI 综合）", 12,
                    "Yahoo Finance 价格序列计算")
    macd_score = _dim_macd(closes, 0)["score"]
    rsi_score = _dim_rsi(closes, 0)["score"]
    parts = [s for s in (trend["score"], macd_score, rsi_score) if s is not None]
    if parts:
        trend["score"] = round(statistics.fmean(parts), 1)
    vol = _dim_vol(closes, 10, name="波动率（HV20）")
    dd = _dim_drawdown(closes, 5, name="牛熊位置（距高点回撤）")
    dd["weight"] = 5
    turnover = _hs_turnover(ctx)
    return [
        _unavailable("valuation", "估值（PE/PB/PEG/ROE）", 15,
                     "东方财富指数估值接口本次不可达", "数据源待接入"),
        _unavailable("earnings", "盈利（EPS/营收/利润率）", 12,
                     "成分股财报聚合无免费 API", "数据源待接入"),
        _unavailable("fund_flow", "资金流（北向/主力）", 12,
                     "北向资金实时披露已取消、历史接口不稳定", "数据源待接入"),
        vol, trend,
        _unavailable("macro", "宏观（LPR/CNY/CPI/GDP）", 10,
                     "官方统计发布无开放 API", "数据源待接入"),
        _unavailable("sector", "行业轮动", 8, "行业指数聚合无免费 API", "数据源待接入"),
        turnover,
        _unavailable("dividend", "股息（股息率/派息率）", 8,
                     "东方财富指数股息率接口本次不可达", "数据源待接入"),
        dd,
    ]


def _hs_turnover(ctx):
    vols = [r["volume"] for r in ctx["prices"] if r.get("volume")]
    if len(vols) < 60:
        return _unavailable("crowding", "拥挤度（换手率）", 8, "Yahoo Finance 成交量",
                            "成交量数据不足")
    ma20 = ind.sma(vols, 20)
    series = [v / m for v, m in zip(vols, ma20) if m]
    return _mk("crowding", "拥挤度（成交量/20日均量）", 8, round(series[-1], 2), "倍",
               ind.percentile_score(series, low_is_high=True),
               "Yahoo Finance (510300.SS 成交量)", "成交清淡代表拥挤度低、情绪冷清")


BUILDERS = {"btc": _btc_dims, "gold": _gold_dims, "nasdaq": _nasdaq_dims,
            "sp500": _sp500_dims, "hs300": _hs300_dims}


def composite(dims: list[dict]) -> tuple[float | None, list[dict]]:
    """Weighted composite over available dims; weights renormalized to 100."""
    avail = [d for d in dims if d["score"] is not None and d["weight"] > 0]
    total_w = sum(d["weight"] for d in avail)
    if not avail or total_w == 0:
        return None, dims
    score = sum(d["score"] * d["weight"] for d in avail) / total_w
    for d in dims:
        d["weight_effective"] = (
            round(d["weight"] / total_w * 100, 1) if d in avail else 0.0
        )
    return round(score, 1), dims
