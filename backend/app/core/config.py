"""Global settings — everything is env-overridable, no secrets needed."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
CACHE_DIR = BASE_DIR / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

API_PREFIX = "/api/v1"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:4173").split(",")
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "20"))
DATA_START = "2015-01-01"
WEEKLY_BASE = 100.0  # backtest base amount per week
