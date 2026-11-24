"""Reference-compatible public data, with explicit live/cache/snapshot provenance.

The reference's server-side scorers are not published. Preserve their outputs
instead of presenting the independent percentile engine as the same algorithm.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import re
import threading
import time

import httpx

from app.core.config import CACHE_DIR
from app.services.market import ASSETS
from app.services.portfolios import PORTFOLIOS
from app.services.reference_rules import hs300_history

REFERENCE_DIR = Path(__file__).resolve().parents[2] / "reference"
MARKET_ZONES = ((20, "极度高估"), (40, "高估"), (60, "合理"), (80, "低估"), (100, "极度低估"))
ENDPOINTS = {
    "markets": "/api/v2/markets",
    **{f"{a}_score": f"/{a}/api/score" for a in ("btc", "gold", "nasdaq", "sp500")},
    "nasdaq_12d": "/nasdaq/api/score-12d",
    "hs300_score": "/hs300/api/hs300/dimensions",
    "hs300_spot": "/hs300/api/hs300/spot",
    "fund_score": "/us-fund-holdings/api/score",
    "hs300_trades": "/hs300/api/robot/trades",
    **{f"{a}_history": f"/{a}/api/history?days=5000" for a in ("btc", "gold", "nasdaq", "sp500")},
}
_memory: dict[str, tuple[float, dict, dict]] = {}
_locks = {k: threading.Lock() for k in (*ENDPOINTS, "funds")}


@lru_cache
def site_data():
    return json.loads((REFERENCE_DIR / "site.json").read_text(encoding="utf-8"))


def _read(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _valid_payload(key, payload):
    if not isinstance(payload, dict) or payload.get("success") is not True:
        return False
    data = payload if key == "nasdaq_12d" else payload.get("data")
    if key == "markets":
        if not isinstance(data, dict):
            return False
        rows = [data[meta["id"]] for meta in ASSETS if meta["id"] in data]
        return bool(rows) and all(
            row is None or isinstance(row, dict) and all(
                type(row.get(field)) in (int, float) and math.isfinite(row[field])
                for field in ("price", "score", "multiplier")
            ) for row in rows
        )
    if key.endswith("_history"):
        return isinstance(data, list) or isinstance(data, dict) and isinstance(data.get("history"), list)
    if key == "hs300_trades":
        return isinstance(data, list)
    if not isinstance(data, dict):
        return False
    field = "score" if key in ("nasdaq_12d", "fund_score") else "compositeScore" if key == "hs300_score" else "totalScore"
    if key == "hs300_spot":
        return isinstance(data.get("price"), (int, float))
    return isinstance(data.get(field), (int, float)) and isinstance(data.get("multiplier"), (int, float))


def _load(key, ttl=60):
    """Bounded network reads; failures never get relabeled as fresh market data."""
    with _locks[key]:
        now = time.monotonic()
        if key in _memory and now - _memory[key][0] < ttl:
            return _memory[key][1:]
        url = "https://btcdca.me" + ENDPOINTS[key]
        path = CACHE_DIR / f"reference_{key}.json"
        envelope = _read(path) or _read(REFERENCE_DIR / f"{key}.json")
        mode, error = "snapshot", None
        try:
            if os.getenv("REFERENCE_OFFLINE") == "1":
                raise httpx.ConnectError("离线模式")
            response = httpx.get(url, timeout=8, follow_redirects=True)
            response.raise_for_status()
            payload = response.json()
            if not _valid_payload(key, payload):
                raise ValueError("参考接口返回无效数据")
            envelope = {"payload": payload, "captured_at": datetime.now(timezone.utc).isoformat(), "url": url}
            mode = "live"
            # A cache write failure must not discard a successful market read.
            try:
                temp = path.with_suffix(".tmp")
                temp.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
                temp.replace(path)
            except OSError:
                pass
        except (httpx.HTTPError, ValueError) as exc:
            error = str(exc)
            mode = "cached" if path.exists() else "snapshot"
        if not envelope:
            return {}, {"mode": "unavailable", "url": url, "error": error}
        provenance = {"mode": mode, "url": url, "captured_at": envelope["captured_at"], "error": error}
        _memory[key] = (now, envelope["payload"], provenance)
        return envelope["payload"], provenance


def _dimension_value(data):
    if "value" in data:
        return data["value"]
    for field in ("pe", "rsi", "vix", "fearGreed"):
        if isinstance(data.get(field), (int, float)):
            return data[field]
    metrics = data.get("metrics", data.get("components", {}))
    for field, child in metrics.items():
        if isinstance(child, dict):
            value = next((child[k] for k in ("value", "rsi", "index", "roe", "yield_10y", "total", "current_pmi", "current") if k in child), None)
            if value is not None:
                return value
        elif isinstance(child, (int, float, str)) and field not in ("source", "note"):
            return child
    return None


def _dimensions(values, weights, names=None):
    return [{"key": key, "name": (names or {}).get(key, d.get("dimension", d.get("name", key))),
             "weight": weights.get(key, 0), "value": _dimension_value(d), "unit": "",
             "score": d.get("score"), "status": "ok" if d.get("score") is not None else "unavailable",
             "source": d.get("dataType", d.get("dataSource", "参考站公开接口")) if isinstance(d.get("dataSource", ""), str) else "参考站公开接口",
             "note": d.get("note", d.get("summary", d.get("status", ""))),
             "details": d} for key, d in values.items() if isinstance(d, dict)]


def _asset(meta, payload, provenance, extra=None):
    asset = meta["id"]
    identity = {k: meta[k] for k in ("id", "name", "name_en", "symbol", "currency")}
    d = payload.get("data", {})
    if not d:
        return {**identity, "status": "unavailable", "dimensions": [], "source": provenance}
    if asset == "hs300":
        dims = {k: v for k, v in d.items() if isinstance(v, dict) and "score" in v}
        weights = {k: v.get("weight", 0) * 100 for k, v in dims.items()}
        dimensions = _dimensions(dims, weights)
        score, price, change = d.get("compositeScore"), d.get("price"), d.get("changePercent")
    elif asset == "sp500":
        details = d.get("detailed_results", {})
        dimensions = _dimensions(details, {k: float(v.get("weight", "0%").strip("%")) for k, v in details.items()})
        score, price, change = d.get("totalScore"), d.get("sp500Price"), d.get("priceChange")
    else:
        weights = {"btc": dict(ahr999=20, ma200=15, mvrv=15, fgi=15, puell=15, reserve=10, hashribbon=10),
                   "gold": dict(dxy=25, tips=20, ma200=18, rsi=12, vix=10, macd=8, seasonality=7),
                   "nasdaq": dict(valuation=35, technical=25, macro=20, sentiment=20)}[asset]
        names = {"ahr999": "AHR999 九神指数", "ma200": "200周均线" if asset == "btc" else "MA200 均线",
                 "mvrv": "MVRV Z-Score", "fgi": "恐惧贪婪指数", "reserve": "Reserve Risk 持币风险",
                 "puell": "Puell 矿工收益比", "hashribbon": "Hash Ribbon 算力丝带",
                 "dxy": "美元指数", "tips": "实际利率", "rsi": "RSI 相对强弱", "vix": "VIX 恐慌指数",
                 "macd": "MACD", "seasonality": "季节性", "valuation": "估值维度", "technical": "技术维度",
                 "macro": "宏观维度", "sentiment": "情绪维度"}
        dimensions = _dimensions(d.get("indicators", {}), weights, names)
        score = d.get("totalScore")
        price = d.get({"btc": "btcPrice", "gold": "goldPrice", "nasdaq": "qqqPrice"}[asset])
        change = d.get("change24h", d.get("priceChange24h", d.get("priceChange")))
    mult = d.get("multiplier")
    zone = d.get("status", d.get("marketStatus", {}).get("level"))
    if not zone and score is not None:
        zone = "极度低估" if score >= 85 else "低估" if score >= 70 else "合理估值" if score >= 50 else "偏高估" if score >= 30 else "极度高估"
    ma = None
    if asset == "btc":
        ratio = d.get("indicators", {}).get("ma200", {}).get("value")
        ma = price / ratio if price and isinstance(ratio, (int, float)) and ratio else None
    elif asset == "gold":
        ma = d.get("indicators", {}).get("ma200", {}).get("ma200")
    return {**identity, "symbol": {"nasdaq": "NDX", "sp500": "SPX", "hs300": "000300"}.get(asset, meta["symbol"]),
            "status": "ok", "price": price, "score": score, "multiplier": mult,
            "date": d.get("lastUpdate", d.get("updateTime", provenance.get("captured_at", "")))[:10],
            "change_pct": change, "zone": zone, "action": d.get("advice", zone),
            "yesterday_score": d.get("yesterdayScore"), "score_change": d.get("scoreChange"),
            "ma200": ma, "ma200_dev_pct": (price / ma - 1) * 100 if ma and price else None,
            "dimensions": dimensions, "source": provenance, "risk_control": d.get("riskControl"),
            "data_quality": d.get("dataQuality"), "raw": d, "secondary": extra}


def get_market():
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda a: _load(f"{a['id']}_score"), ASSETS))
    return {"assets": [_asset(m, payload, source) for m, (payload, source) in zip(ASSETS, results)]}


def get_market_overview():
    payload, source = _load("markets", ttl=25)
    data = payload.get("data", {})
    data_at = data.get("lastUpdate") or payload.get("timestamp") or payload.get("generatedAt")
    if isinstance(data_at, (int, float)):
        try:
            data_at = datetime.fromtimestamp(data_at / 1000, tz=timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            data_at = None
    if not isinstance(data_at, str):
        data_at = None
    assets = []
    for meta in ASSETS:
        row = data.get(meta["id"]) or {}
        score = row.get("score")
        zone = next((label for limit, label in MARKET_ZONES if score is not None and score <= limit), None)
        assets.append({
            **{key: meta[key] for key in ("id", "name", "name_en", "symbol", "currency")},
            "symbol": row.get("symbol", meta["symbol"]),
            "status": "ok" if row else "unavailable",
            "price": row.get("price"), "change_pct": row.get("change24h"),
            "score": score, "multiplier": row.get("multiplier"),
            "zone": zone, "action": row.get("strategy") or row.get("status"),
            "date": (row.get("updatedAt") or data_at) if row else None,
            "source": source,
        })
    return {"assets": assets, "source": source, "data_at": data_at}


def get_history(asset):
    if asset == "hs300":
        rows = site_data()["reports"][asset].get("monthlyData", [])
        return hs300_history(rows), {"mode": "report", "url": "https://btcdca.me/hs300/"}
    payload, source = _load(f"{asset}_history", ttl=3600)
    data = payload.get("data", [])
    rows = data.get("history", []) if isinstance(data, dict) else data
    out = []
    for r in rows:
        price = next((r[k] for k in ("btcPrice", "gold_price", "ndxPrice", "qqqPrice", "ndx_price", "spxPrice", "spx_price", "sp500Price", "price") if r.get(k) is not None), None)
        out.append({"date": r["date"][:10], "price": price,
                    "score": r.get("totalScore", r.get("total_score")), "multiplier": r.get("multiplier"),
                    "fgi": r.get("fgi_value", r.get("fearGreed", r.get("fgi"))),
                    **{field: r.get(field) for field in ("pe", "pb", "rsi")},
                    "dxy": r.get("dxy_value", r.get("dxy")), "vix": r.get("vix_value", r.get("vix")),
                    "tips": r.get("tips_yield", r.get("tips")),
                    "event": r.get("eventType", r.get("event_type", ""))})
    return sorted(out, key=lambda r: r["date"]), source


def _detail_recommendation(asset, raw):
    score, multiplier = raw["totalScore"], raw["multiplier"]
    if asset == "btc":
        zone = next(text for limit, text in ((85, "极度低估"), (70, "偏低估"), (50, "合理估值"),
                                             (30, "偏高估"), (-float("inf"), "极度高估")) if score >= limit)
        action = "增配" if multiplier >= 1.5 else "标配" if multiplier >= 1 else "低配"
        return zone, f"当前综合评分 {score:g} 分，市场处于{zone}区间。建议今日定投 {multiplier:g}x（{action}）。"
    if asset == "gold":
        zone = next((text for limit, text in ((85, "极度低估"), (70, "低估"), (55, "合理估值"),
                                              (45, "轻微高估"), (30, "高估")) if score >= limit), "极度高估")
        action = next((text for limit, text in ((2.5, "大幅加仓"), (1.5, "适当加仓"), (1, "标准定投"),
                                                (.7, "保守参与")) if multiplier >= limit), "减少投入")
        return raw.get("marketStatus", {}).get("level", zone), f"当前综合评分 {score:g} 分，市场处于{zone}区间。建议今日定投操作 {multiplier:.2f}x（{action}）。"
    extreme, low = (85, 70) if asset == "nasdaq" else (80, 65)
    zone = next((text for limit, text in ((extreme, "极度低估"), (low, "低估"), (50, "合理估值"),
                                         (35, "轻微高估")) if score >= limit), "极度高估")
    action = next((text for limit, text in ((2, "重仓投入"), (1.5, "增持"), (1, "标准定投"),
                                           (.5, "保守定投")) if multiplier >= limit), "暂停定投")
    return raw.get("eventType") or raw.get("status") or zone, f"当前综合评分 {score:g} 分，市场处于{zone}区间。建议今日定投 {multiplier:g}x（{action}）。"


def get_asset(asset):
    meta = next((m for m in ASSETS if m["id"] == asset), None)
    if not meta:
        return None
    payload, source = _load(f"{asset}_score")
    extra = None
    if asset == "nasdaq":
        raw, src = _load("nasdaq_12d")
        names = {d["key"]: d["label"] for d in site_data()["reports"]["nasdaq"].get("DIM12_CONFIG", [])}
        extra = {"score": raw.get("score"), "multiplier": raw.get("multiplier"), "source": src,
                 "dimensions": _dimensions(raw.get("dimensions", {}), raw.get("weights", {}), names)}
    detail = _asset(meta, payload, source, extra)
    raw = payload.get("data", {})
    if raw and asset != "hs300":
        detail["zone"], detail["action"] = _detail_recommendation(asset, raw)
    indicators = raw.get("indicators", {})
    if asset in ("nasdaq", "sp500"):
        detail.update(valuation={k: indicators.get("valuation", {}).get(k) for k in ("pe", "pb")})
    if asset == "sp500":
        detail["summary_indicators"] = _dimensions(
            indicators, {}, {"valuation": "估值维度", "technical": "技术维度", "macro": "宏观维度", "sentiment": "情绪维度"})
    history, history_source = get_history(asset)
    detail.update(history=history, history_source=history_source, report=site_data()["reports"][asset])
    if asset == "hs300":
        report = dict(detail["report"])
        if history:
            report.update(growthLabels=[r["date"] for r in history],
                          strategyValue=[r["value"] for r in history],
                          standardValue=[r["regular_value"] for r in history],
                          bhValue=[r["buyhold_value"] for r in history],
                          capital_invested=[history[-1]["invested"], history[-1]["regular_invested"], history[-1]["buyhold_invested"]],
                          capital_profit=[history[-1]["value"] - history[-1]["invested"],
                                          history[-1]["regular_value"] - history[-1]["regular_invested"],
                                          history[-1]["buyhold_value"] - history[-1]["buyhold_invested"]])
        detail["report"] = report
        trades, src = _load("hs300_trades", ttl=300)
        detail.update(trades=trades.get("data", []), trades_source=src)
    return detail


def get_fund_data():
    with _locks["funds"]:
        now = time.monotonic()
        if "funds" in _memory and now - _memory["funds"][0] < 3600:
            return _memory["funds"][1:]
        path = CACHE_DIR / "reference_funds.json"
        envelope = _read(path)
        data = envelope["payload"] if envelope else site_data()["funds"]
        source = {"mode": "snapshot", "url": "https://btcdca.me/us-fund-holdings/",
                  "captured_at": envelope["captured_at"] if envelope else site_data()["captured_at"]}
        try:
            if os.getenv("REFERENCE_OFFLINE") == "1":
                raise httpx.ConnectError("离线模式")
            response = httpx.get(source["url"], timeout=10)
            response.raise_for_status()
            match = re.search(r"const\s+FUND_DATA\s*=\s*", response.text)
            if not match:
                raise ValueError("Missing fund dataset")
            candidate, _ = json.JSONDecoder().raw_decode(response.text[match.end():])
            if not candidate.get("funds") or not candidate.get("passiveFunds"):
                raise ValueError("Incomplete fund dataset")
            data = candidate
            source.update(mode="live", captured_at=datetime.now(timezone.utc).isoformat())
            try:
                temp = path.with_suffix(".tmp")
                temp.write_text(json.dumps({"payload": data, "captured_at": source["captured_at"]}, ensure_ascii=False), encoding="utf-8")
                temp.replace(path)
            except OSError:
                pass
        except (httpx.HTTPError, ValueError) as exc:
            source["error"] = str(exc)
            source["mode"] = "cached" if envelope else "snapshot"
        _memory["funds"] = (now, data, source)
        return data, source


def get_funds(kind):
    data, source = get_fund_data()
    rows = data["funds" if kind == "active" else "passiveFunds"]
    out = []
    for f in rows:
        extra = data.get("extra", {}).get(f["name"], f)
        risk = extra.get("risk", {})
        perf = extra.get("perf", {})
        out.append({"code": f["code"], "name": f["name"], "kind": kind, "status": "ok",
                    "scale_yi": f.get("scale"), "inception": f.get("estabDate"),
                    "total_return_pct": f.get("totalReturn"), "annualized_pct": f.get("cagr"),
                    "daily_change_pct": f.get("change"), "max_drawdown_pct": f.get("maxDrawdown"),
                    "purchase_limit": f.get("dailyLimit"), "benchmark_cagr_pct": f.get("nasdaq100Cagr"),
                    "excess_return_pct": f.get("excessReturn"), "beat_benchmark": f.get("beatNasdaq"),
                    "returns": {a: perf.get(b) for a, b in {"1m":"m1", "3m":"m3", "6m":"m6", "1y":"y1", "3y":"y3", "5y":"y5", "all":"all"}.items()},
                    "risk": {"sharpe": risk.get("sharpe"), "volatility_pct": risk.get("volatility"),
                             "beta": risk.get("beta"), "alpha": risk.get("alpha"), "as_of": risk.get("asOf")},
                    "allocation": {name: extra.get("alloc", {}).get(key) for key, name in {"stock":"股票", "bond":"债券", "cash":"现金及其他"}.items()},
                    "manager": extra.get("manager"), "fees": extra.get("fee"),
                    "holdings_top10": data.get("holdingsTop10", {}).get(f["name"]) if kind == "active" else None,
                    "holdings_full": data.get("holdings", {}).get(f["name"]), "source": source})
    return out


def get_portfolios():
    ids = [m["id"] for m in PORTFOLIOS]
    out = []
    for id_, p in zip(ids, site_data()["portfolios"]):
        holdings = [(re.search(r'\(([^)]+)\)', a["n"])[1], a) for a in p["alloc"]]
        allocation = {ticker: a["p"] for ticker, a in holdings}
        risk_level = 1 + sum(p["vol"] >= threshold for threshold in (8, 10, 12, 14))
        value, growth = 10000, []
        for year, ret in zip(range(2017, 2026), p["annual"]):
            value *= 1 + ret / 100
            growth.append({"date": str(year), "value": int(value + 0.5)})
        out.append({"id": id_, "name": p["name"], "name_en": p["nameEn"], "risk": "低" if p["vol"] < 10 else "中" if p["vol"] < 14 else "高",
                    "risk_level": risk_level, "ticker": p["ticker"], "allocation": allocation,
                    "allocation_labels": {ticker: a["n"] for ticker, a in holdings},
                    "status": "ok", "annualized_pct": p["cagr"], "volatility_pct": p["vol"],
                    "max_drawdown_pct": p["mdd"], "sharpe": p["sharpe"], "sortino": p["sortino"],
                    "beta": p["beta"], "alpha": p["alpha"], "r2": p["r2"], "best": p["best"], "worst": p["worst"],
                    "founder": p["founder"], "note": p["desc"], "philosophy": p["philosophy"], "period": "2017–2025",
                    "initial": 10000, "final_value": growth[-1]["value"], "growth_curve": growth,
                    "yearly": dict(zip(map(str, range(2017, 2026)), p["annual"])),
                    "stress_tests": site_data()["portfolio_stress"][p["key"]],
                    "source": {"mode": "report", "url": "https://btcdca.me/lazy/", "captured_at": site_data()["captured_at"]}})
    return out
