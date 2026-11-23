from fastapi import APIRouter, HTTPException

from app import cache

router = APIRouter(tags=["portfolios"])

_SUMMARY_KEYS = ("id", "name", "risk", "allocation", "status", "annualized_pct",
                 "volatility_pct", "max_drawdown_pct", "sharpe", "period")


@router.get("/portfolios")
def list_portfolios():
    return [{k: p.get(k) for k in _SUMMARY_KEYS} for p in cache.get_portfolios()]


@router.get("/portfolios/{portfolio_id}")
def portfolio_detail(portfolio_id: str):
    for p in cache.get_portfolios():
        if p["id"] == portfolio_id:
            return p
    raise HTTPException(404, f"unknown portfolio: {portfolio_id}")
