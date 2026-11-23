"""External free data sources: alternative.me, CoinMetrics, FRED, EastMoney.

Every function returns [] / None on failure — callers mark the dimension
'unavailable' instead of inventing data.
"""
from __future__ import annotations

import csv
import io
import json
import re
import urllib.request

from app.core.config import HTTP_TIMEOUT

_UA = {"User-Agent": "Mozilla/5.0"}


def _get(url: str, headers: dict | None = None, timeout: float | None = None) -> bytes:
    req = urllib.request.Request(url, headers={**_UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout or HTTP_TIMEOUT) as r:
        return r.read()


def fear_greed_series() -> list[dict]:
    """Crypto Fear & Greed index history (alternative.me). [{date, value}]"""
    try:
        data = json.loads(_get("https://api.alternative.me/fng/?limit=0&format=json"))
        rows = [
            {
                "date": __import__("datetime").datetime.fromtimestamp(
                    int(d["timestamp"])
                ).strftime("%Y-%m-%d"),
                "value": float(d["value"]),
            }
            for d in data["data"]
        ]
        return sorted(rows, key=lambda x: x["date"])
    except Exception:
        return []


def coinmetrics_series(metric: str, start: str = "2015-01-01") -> list[dict]:
    """CoinMetrics community API, one BTC metric. [{date, value}]"""
    url = (
        "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
        f"?assets=btc&metrics={metric}&frequency=1d&page_size=10000&start_time={start}"
    )
    try:
        data = json.loads(_get(url))
        rows = []
        for d in data.get("data", []):
            v = d.get(metric)
            if v is not None:
                rows.append({"date": d["time"][:10], "value": float(v)})
        return rows
    except Exception:
        return []


def fred_series(series_id: str, start: str = "2010-01-01") -> list[dict]:
    """FRED fredgraph CSV without API key. [{date, value}]"""
    try:
        raw = _get(
            f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start}",
            timeout=30,
        ).decode()
        rows = []
        for row in csv.DictReader(io.StringIO(raw)):
            v = row.get(series_id, "")
            if v and v != ".":
                rows.append({"date": row["DATE"], "value": float(v)})
        return rows
    except Exception:
        return []


_EM_HEADERS = {"Referer": "https://fundf10.eastmoney.com/"}


def eastmoney_fundcode_search() -> list[list]:
    """All funds from EastMoney: [code, abbr, name, type, pinyin]."""
    try:
        raw = _get("https://fund.eastmoney.com/js/fundcode_search.js").decode("utf-8-sig")
        return json.loads(raw[raw.index("[[") : raw.rindex("]]") + 2])
    except Exception:
        return []


def eastmoney_pingzhongdata(code: str) -> str:
    """Raw pingzhongdata JS for one fund (NAV trend, manager, scale...)."""
    try:
        return _get(f"https://fund.eastmoney.com/pingzhongdata/{code}.js", _EM_HEADERS).decode(
            "utf-8", "ignore"
        )
    except Exception:
        return ""


def extract_js_var(js: str, name: str):
    """Extract `var <name> = <json>;` from EastMoney pingzhongdata JS
    using balanced-bracket scanning (values contain nested arrays)."""
    m = re.search(rf"var {re.escape(name)}\s*=\s*", js)
    if not m:
        return None
    i = m.end()
    if i >= len(js):
        return None
    if js[i] not in "[{":
        m2 = re.match(r'"[^"]*"|[\d.]+', js[i:])
        try:
            return json.loads(m2.group(0)) if m2 else None
        except Exception:
            return None
    depth, in_str, esc = 0, False, False
    for j in range(i, len(js)):
        ch = js[j]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(js[i : j + 1])
                except Exception:
                    return None
    return None
