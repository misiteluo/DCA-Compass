"""Pydantic response schemas for the summary-level endpoints.
Asset detail / funds / portfolios return rich nested dicts built by the
service layer (documented in README); summary models below pin the
stable fields the frontend relies on."""
from __future__ import annotations

from pydantic import BaseModel


class AssetSummary(BaseModel):
    id: str
    name: str
    name_en: str
    symbol: str
    currency: str
    status: str
    price: float | None = None
    change_pct: float | None = None
    date: str | None = None
    score: float | None = None
    multiplier: float | None = None
    zone: str | None = None
    action: str | None = None
    source: dict | None = None


class MarketOverview(BaseModel):
    assets: list[AssetSummary]
    source: dict
    data_at: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
