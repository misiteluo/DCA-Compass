from fastapi import APIRouter, HTTPException, Query

from app import cache
from app.services.funds import build_fund_detail

router = APIRouter(tags=["funds"])

_LIST_KEYS = ("code", "name", "kind", "status", "scale_yi", "inception",
              "total_return_pct", "annualized_pct", "daily_change_pct",
              "max_drawdown_pct", "purchase_limit")


@router.get("/funds")
def list_funds(kind: str = Query("active", pattern="^(active|passive)$")):
    funds = cache.get_funds(kind)
    return [{k: f.get(k) for k in _LIST_KEYS} for f in funds]


@router.get("/funds/{code}")
def fund_detail(code: str):
    detail = build_fund_detail(code)
    if detail is None:
        raise HTTPException(404, f"unknown fund: {code}")
    return detail
