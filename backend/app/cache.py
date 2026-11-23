"""Daily file cache. Data is rebuilt at most once per calendar day;
the FastAPI app triggers a rebuild on first request after midnight."""
from __future__ import annotations

import json
import threading
from datetime import date
from pathlib import Path

from app.core.config import CACHE_DIR

_lock = threading.Lock()


def _load(name: str, builder) -> dict | list:
    path = Path(CACHE_DIR) / f"{name}.json"
    today = date.today().isoformat()
    with _lock:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("_cached_date") == today:
                    return data["payload"]
            except Exception:
                pass
        payload = builder()
        path.write_text(json.dumps({"_cached_date": today, "payload": payload},
                                   ensure_ascii=False), encoding="utf-8")
        return payload


def get_market() -> dict:
    from app.services.market import build_market

    return _load("market", build_market)  # type: ignore[return-value]


def get_portfolios() -> list:
    from app.services.portfolios import build_portfolios

    return _load("portfolios", build_portfolios)  # type: ignore[return-value]


def get_funds(kind: str) -> list:
    from app.services.funds import build_funds

    return _load(f"funds_{kind}", lambda: build_funds(kind))  # type: ignore[return-value]
