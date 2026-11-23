from fastapi import APIRouter, HTTPException

from app.services import reference

router = APIRouter(tags=["portfolios"])

@router.get("/portfolios")
def list_portfolios():
    return reference.get_portfolios()


@router.get("/portfolios/{portfolio_id}")
def portfolio_detail(portfolio_id: str):
    for p in reference.get_portfolios():
        if p["id"] == portfolio_id:
            return p
    raise HTTPException(404, f"unknown portfolio: {portfolio_id}")
