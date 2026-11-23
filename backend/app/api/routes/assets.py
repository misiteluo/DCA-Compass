from fastapi import APIRouter, HTTPException

from app import cache
from app.schemas.models import AssetSummary

router = APIRouter(tags=["assets"])

_SUMMARY_KEYS = ("id", "name", "name_en", "symbol", "currency", "status",
                 "price", "change_pct", "date", "score", "multiplier", "zone", "action")


@router.get("/assets", response_model=list[AssetSummary])
def list_assets():
    market = cache.get_market()
    return [{k: a.get(k) for k in _SUMMARY_KEYS} for a in market["assets"]]


@router.get("/assets/{asset_id}")
def asset_detail(asset_id: str):
    market = cache.get_market()
    for a in market["assets"]:
        if a["id"] == asset_id:
            return a
    raise HTTPException(404, f"unknown asset: {asset_id}")
