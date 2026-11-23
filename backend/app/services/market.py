"""Market orchestration: fetch everything once, build all asset details."""
from __future__ import annotations

from app.services import backtest as bt
from app.services import scoring
from app.services.providers import external, yahoo

ASSETS = [
    {"id": "btc", "name": "比特币", "name_en": "Bitcoin", "symbol": "BTC-USD",
     "currency": "$", "config": {"principal": "$1,000,000", "period": "10 年", "monthly": "$8,333"},
     "risk_rules": ["单周定投倍数上限 3.0x", "连续 7 日高评分后自动降一档",
                    "回撤达 30% 时暂停一天新增定投", "BTC 仓位不超过总资产 20%"]},
    {"id": "gold", "name": "黄金", "name_en": "Gold", "symbol": "GC=F",
     "currency": "$", "config": {"principal": "$1,000,000", "period": "10 年", "monthly": "$8,333"},
     "risk_rules": ["单周定投倍数上限 3.0x", "连续 5 日评分高于 85 后降档至 2.5x",
                    "金价回撤 12% 触发熔断，倍数回归 1.0x", "黄金仓位不超过流动资产 20%"]},
    {"id": "nasdaq", "name": "纳斯达克100", "name_en": "Nasdaq-100", "symbol": "QQQ",
     "currency": "$", "config": {"principal": "$1,000,000", "period": "10 年", "monthly": "$2,600"},
     "risk_rules": ["单次定投倍数上限 2.5x", "连续 5 个交易日评分高于 90 后降档至 2.0x",
                    "回撤 15% 触发熔断，倍数回归 1.0x", "纳指仓位不超过流动资产 25%"]},
    {"id": "sp500", "name": "标普500", "name_en": "S&P 500", "symbol": "SPY",
     "currency": "$", "config": {"principal": "$1,000,000", "period": "10 年", "monthly": "$8,333"},
     "risk_rules": ["单次定投倍数上限 2.25x", "连续 5 日评分不低于 90 后降档至 2.0x",
                    "回撤 15% 触发熔断，倍数回归 1.0x", "标普500 仓位不超过流动资产 35%"]},
    {"id": "hs300", "name": "沪深300", "name_en": "CSI 300", "symbol": "510300.SS",
     "currency": "¥", "config": {"principal": "¥1,000,000", "period": "10 年", "monthly": "¥8,333"},
     "risk_rules": ["单次投入不超过月收入 30%", "评分高于 80 时逐步减仓",
                    "评分低于 20 时暂停定投", "最大回撤超过 30% 启动紧急避险", "每季度复盘调整参数"]},
]


def _values(rows: list[dict]) -> list[float]:
    return [r["close"] for r in rows]


def build_market() -> dict:
    aux = {
        "vix": _values(yahoo.fetch_series("^VIX", "2015-01-01")),
        "dxy": _values(yahoo.fetch_series("DX-Y.NYB", "2015-01-01")),
        "tnx": _values(yahoo.fetch_series("^TNX", "2015-01-01")),
        "fgi": external.fear_greed_series(),
        "tips": external.fred_series("DFII10"),
        "will5000": external.fred_series("WILL5000INDFC"),
        "gdp": external.fred_series("GDP"),
    }
    btc_ext = {
        "mvrv": external.coinmetrics_series("CapMVRVCur"),
        "issuance": external.coinmetrics_series("IssTotUSD"),
        "hashrate": external.coinmetrics_series("HashRate"),
    }
    assets = []
    for meta in ASSETS:
        prices = yahoo.fetch_series(meta["symbol"])
        if not prices:
            assets.append({**meta, "status": "unavailable", "dimensions": []})
            continue
        closes = _values(prices)
        ctx = {"closes": closes, "dates": [r["date"] for r in prices], "prices": prices,
               "vix": aux["vix"], "dxy": aux["dxy"], "tnx": aux["tnx"], "fgi": aux["fgi"],
               "tips": aux["tips"], "will5000": aux["will5000"], "gdp": aux["gdp"],
               **btc_ext}
        dims = scoring.BUILDERS[meta["id"]](ctx)
        score, dims = scoring.composite(dims)
        mult = scoring.multiplier(meta["id"], score) if score is not None else None
        zone, action = scoring.zone_of(score) if score is not None else ("数据不足", "观望")
        prev = closes[-2] if len(closes) > 1 else closes[-1]
        ma200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else None
        assets.append({
            **meta, "status": "ok",
            "price": closes[-1], "prev_close": prev,
            "change_pct": round((closes[-1] / prev - 1) * 100, 2),
            "date": prices[-1]["date"],
            "ma200": round(ma200, 2) if ma200 else None,
            "ma200_dev_pct": round((closes[-1] / ma200 - 1) * 100, 2) if ma200 else None,
            "score": score, "multiplier": mult, "zone": zone, "action": action,
            "dimensions": dims,
            "mapping_table": scoring.mapping_table(meta["id"]),
            "price_history": [{"date": r["date"], "close": r["close"]} for r in prices[::5]],
            "backtest": bt.run_backtest(meta["id"], prices),
        })
    return {"assets": assets}
