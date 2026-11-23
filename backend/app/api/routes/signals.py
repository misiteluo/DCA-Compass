from fastapi import APIRouter

from app.services import reference

router = APIRouter(tags=["signals"])


@router.get("/signals/weekly")
def weekly_signals():
    market = reference.get_market()
    rows = [
        {"asset_id": a["id"], "name": a["name"], "score": a.get("score"),
         "zone": a.get("zone"), "multiplier": a.get("multiplier"),
         "action": a.get("action"), "price": a.get("price"), "date": a.get("date")}
        for a in market["assets"]
    ]
    return {"signals": rows}
