"""定投罗盘 DCA Compass API — entry point.

Run: uvicorn app.main:app --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import assets, funds, health, portfolios, signals
from app.core.config import API_PREFIX, CORS_ORIGINS

app = FastAPI(title="定投罗盘 DCA Compass API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)
for r in (health, assets, signals, funds, portfolios):
    app.include_router(r.router, prefix=API_PREFIX)
