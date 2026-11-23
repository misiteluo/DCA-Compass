"""Yahoo Finance chart API provider (free, no key). Returns daily bars."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from app.core.config import HTTP_TIMEOUT

_HOSTS = ("query1.finance.yahoo.com", "query2.finance.yahoo.com")


def fetch_series(symbol: str, start: str = "2015-01-01") -> list[dict]:
    """Daily bars: [{date, close, volume}] ascending. [] on failure."""
    p1 = int(datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp())
    p2 = int(time.time()) + 86400
    q = urllib.parse.urlencode({"period1": p1, "period2": p2, "interval": "1d"})
    sym = urllib.parse.quote(symbol, safe="")
    for host in _HOSTS:
        try:
            req = urllib.request.Request(
                f"https://{host}/v8/finance/chart/{sym}?{q}",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
                payload = json.load(r)
            result = payload["chart"]["result"][0]
            ts = result["timestamp"]
            quote = result["indicators"]["quote"][0]
            closes, volumes = quote["close"], quote.get("volume") or [None] * len(ts)
            rows = []
            for t, c, v in zip(ts, closes, volumes):
                if c is None:
                    continue
                rows.append({
                    "date": datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d"),
                    "close": float(c),
                    "volume": float(v) if v else None,
                })
            if rows:
                return rows
        except Exception:
            continue
    return []
