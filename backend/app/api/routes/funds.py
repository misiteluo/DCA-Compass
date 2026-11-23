from fastapi import APIRouter, HTTPException, Query

from app.services import reference

router = APIRouter(tags=["funds"])

@router.get("/funds")
def list_funds(kind: str = Query("active", pattern="^(active|passive)$")):
    return reference.get_funds(kind)


@router.get("/fund-market-score")
def fund_market_score():
    payload, source = reference._load("fund_score", ttl=300)
    return {**payload.get("data", {}), "source": source}


@router.get("/funds/{code}")
def fund_detail(code: str):
    detail = next((f for kind in ("active", "passive") for f in reference.get_funds(kind) if f["code"] == code), None)
    if detail is None:
        raise HTTPException(404, f"unknown fund: {code}")
    return detail
