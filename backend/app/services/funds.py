"""QDII fund universe (EastMoney public data).

Fund names/codes are public facts. All performance numbers are computed
from the fund's real NAV trend (pingzhongdata); anything that cannot be
parsed is returned as None and shown as '--' — never invented.
"""
from __future__ import annotations

import math
import statistics
from datetime import datetime, timedelta, timezone

from app.services.providers import external

# 16 passive Nasdaq-100 index C-class (RMB) funds, verified 2026-11-23
# against EastMoney's fund catalogue (one per manager where possible).
PASSIVE_CODES = [
    "006479", "008971", "012752", "012870", "014978", "015300", "016057",
    "016453", "016533", "018044", "018967", "019173", "019442", "019525",
    "019548", "019737",
]

# The original page's 23 actively-managed US-equity QDII funds (code list).
ACTIVE_CODES = [
    "270023", "000043", "017436", "012920", "161128", "005698", "006373",
    "017091", "040025", "001668", "016701", "539002", "006555", "018036",
    "017730", "100055", "501312", "002268", "457001", "016664", "017696",
    "008253", "017144",
]


def _nav_stats(trend: list[dict]) -> dict:
    """trend: Data_netWorthTrend [{x: ms, y: unit NAV, equityReturn: cum %}]."""
    if not trend:
        return {}
    navs = [float(t["y"]) for t in trend]
    dates = [datetime.fromtimestamp(t["x"] / 1000, timezone.utc) for t in trend]
    total = (navs[-1] / navs[0] - 1) * 100
    years = max((dates[-1] - dates[0]).days / 365.25, 0.01)
    peak, dd = navs[0], 0.0
    for v in navs:
        peak = max(peak, v)
        dd = min(dd, (v / peak - 1) * 100)
    daily = (navs[-1] / navs[-2] - 1) * 100 if len(navs) > 1 else None

    def ret(days: int):
        target = dates[-1] - timedelta(days=days)
        past = next((n for d, n in zip(dates, navs) if d >= target), None)
        return round((navs[-1] / past - 1) * 100, 2) if past else None

    weekly = navs[::5]
    wrets = [weekly[i] / weekly[i - 1] - 1 for i in range(1, len(weekly))]
    sd = statistics.pstdev(wrets) if len(wrets) > 20 else 0.0
    mean = statistics.fmean(wrets) if wrets else 0.0
    return {
        "inception": dates[0].strftime("%Y-%m-%d"),
        "total_return_pct": round(total, 2),
        "annualized_pct": round(((navs[-1] / navs[0]) ** (1 / years) - 1) * 100, 2),
        "max_drawdown_pct": round(dd, 2),
        "daily_change_pct": round(daily, 2) if daily is not None else None,
        "returns": {"1m": ret(30), "3m": ret(91), "6m": ret(182),
                    "1y": ret(365), "3y": ret(365 * 3), "5y": ret(365 * 5)},
        "risk": {
            "sharpe": round(mean / sd * math.sqrt(52), 2) if sd else None,
            "volatility_pct": round(sd * math.sqrt(52) * 100, 2) if sd else None,
            "beta": None, "alpha": None,
            "note": "贝塔/阿尔法需基准对齐计算，暂未接入" ,
        },
    }


def _fund_from_pingzhong(code: str, name: str, kind: str) -> dict:
    js = external.eastmoney_pingzhongdata(code)
    base = {"code": code, "name": name, "kind": kind, "status": "ok" if js else "unavailable"}
    if not js:
        return base
    trend = external.extract_js_var(js, "Data_netWorthTrend") or []
    base.update(_nav_stats(trend))
    scale = external.extract_js_var(js, "Data_fluctuationScale")
    if isinstance(scale, dict) and scale.get("series"):
        last = scale["series"][-1]
        base["scale_yi"] = last.get("y") if isinstance(last, dict) else None
    elif isinstance(scale, list) and scale:
        base["scale_yi"] = scale[-1].get("y")
    managers = external.extract_js_var(js, "Data_currentFundManager")
    if isinstance(managers, list) and managers:
        m = managers[0]
        base["manager"] = {"name": m.get("name"), "tenure": m.get("workTime")}
    alloc = external.extract_js_var(js, "Data_assetAllocation")
    if isinstance(alloc, dict):
        cats = alloc.get("categories", [])
        data = alloc.get("series", [])
        if cats and data:
            latest = {s["name"]: s["data"][-1] for s in data if s.get("data")}
            base["allocation"] = latest
    base["fees"] = None  # fee schedule not exposed by this endpoint
    base["purchase_limit"] = None  # daily limit changes daily; shown as --
    return base


def build_funds(kind: str) -> list[dict]:
    catalogue = external.eastmoney_fundcode_search()
    by_code = {row[0]: row[2] for row in catalogue}
    if kind == "active":
        codes = ACTIVE_CODES
    else:
        codes = [c for c in PASSIVE_CODES if c in by_code]
    return [_fund_from_pingzhong(c, by_code.get(c, c), kind) for c in codes]


def build_fund_detail(code: str) -> dict | None:
    catalogue = external.eastmoney_fundcode_search()
    by_code = {row[0]: row[2] for row in catalogue}
    if code not in by_code:
        return None
    kind = "active" if code in ACTIVE_CODES else "passive"
    return _fund_from_pingzhong(code, by_code[code], kind)
