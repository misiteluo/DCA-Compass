from fastapi import APIRouter, HTTPException

from app.services import reference
from app.schemas.models import AssetSummary

router = APIRouter(tags=["assets"])

_SUMMARY_KEYS = ("id", "name", "name_en", "symbol", "currency", "status",
                 "price", "change_pct", "date", "score", "multiplier", "zone", "action", "source")


@router.get("/assets", response_model=list[AssetSummary])
def list_assets():
    market = reference.get_market()
    return [{k: a.get(k) for k in _SUMMARY_KEYS} for a in market["assets"]]


@router.get("/assets/{asset_id}")
def asset_detail(asset_id: str):
    detail = reference.get_asset(asset_id)
    if detail is not None:
        return detail
    raise HTTPException(404, f"unknown asset: {asset_id}")
