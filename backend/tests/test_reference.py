"""Golden public responses, local recovered rules, API boundaries and fallback."""
import importlib.util
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import reference
from app.services.reference_rules import hs300_history, hs300_multiplier, hs300_valuation


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    monkeypatch.setenv("REFERENCE_OFFLINE", "1")
    monkeypatch.setattr(reference, "CACHE_DIR", tmp_path)
    reference._memory.clear()
    yield
    reference._memory.clear()


def test_five_asset_public_outputs_are_preserved():
    client = TestClient(app)
    rows = client.get("/api/v1/assets").json()
    expected = {"btc": (82, 1.64, 7), "gold": (60, 1.125, 7),
                "nasdaq": (63, 1, 4), "sp500": (60, 1.27, 10), "hs300": (68, 1.5, 10)}
    assert len(rows) == 5
    for row in rows:
        score, multiplier, dimensions = expected[row["id"]]
        assert (row["score"], row["multiplier"]) == (score, multiplier)
        assert row["source"]["mode"] == "snapshot"
        detail = client.get(f"/api/v1/assets/{row['id']}").json()
        assert len(detail["dimensions"]) == dimensions
        assert detail["history"] == sorted(detail["history"], key=lambda r: r["date"])
        assert detail["report"]["tables"]
        assert detail["report"]["strategy"]
    nasdaq = client.get("/api/v1/assets/nasdaq").json()
    assert len(nasdaq["secondary"]["dimensions"]) == 12
    assert nasdaq["secondary"]["score"] == 64
    assert nasdaq["risk_control"]["active"] is True
    assert nasdaq["valuation"]["pb"] is not None
    assert len(nasdaq["report"]["comparison_years"]) == len(nasdaq["report"]["strategyReturns"]) == 12
    assert nasdaq["report"]["total_returns"] == [120.18, 93.45, 294.86]
    gold = client.get("/api/v1/assets/gold").json()
    assert {k: gold["history"][-1][k] for k in ("dxy", "vix", "tips")} == {"dxy": 104, "vix": 29.8, "tips": 1.8}
    sp500 = client.get("/api/v1/assets/sp500").json()
    assert len(sp500["summary_indicators"]) == 4
    assert sp500["history"][-1]["rsi"] == 29.17
    heatmap = sp500["report"]["monthly_heatmap"]
    assert list(heatmap) == [str(year) for year in range(2015, 2026)]
    assert all(len(months) == 12 for months in heatmap.values())
    assert heatmap["2015"][:2] == [-1.2, 4.1]
    btc = client.get("/api/v1/assets/btc").json()
    assert btc["ma200"] == pytest.approx(btc["price"] / .9)
    assert btc["zone"] == "偏低估" and "1.64x（增配）" in btc["action"]
    assert btc["report"]["risk_return"][0] == {"name": "策略DCA", "drawdown": 83.1, "return_pct": 5573}


def test_homepage_uses_the_aggregate_market_feed():
    client = TestClient(app)
    markets = client.get("/api/v1/markets").json()
    assert markets["source"]["mode"] == "snapshot"
    assert markets["data_at"].endswith("Z")
    rows = {row["id"]: row for row in markets["assets"]}
    assert (rows["nasdaq"]["score"], rows["nasdaq"]["multiplier"], rows["nasdaq"]["zone"]) == (59, 1.12, "合理")
    assert rows["hs300"]["status"] == "unavailable"
    assert rows["hs300"]["score"] is None
    assert client.get("/api/v1/assets/hs300").json()["score"] == 68


def test_market_cache_keeps_zero_and_reports_fallback(monkeypatch):
    monkeypatch.delenv("REFERENCE_OFFLINE")
    feed = {"success": True, "timestamp": 1795446850011,
            "data": {"btc": {"price": 10, "score": 0, "multiplier": 0}, "gold": None}}
    monkeypatch.setattr(reference.httpx, "get", lambda url, **kwargs: httpx.Response(
        200, json=feed, request=httpx.Request("GET", url)))
    markets = reference.get_market_overview()
    assert markets["source"]["mode"] == "live"
    assert markets["assets"][0]["multiplier"] == 0
    assert markets["assets"][0]["date"] == "2026-11-23T15:14:10.011000+00:00"
    reference._memory.clear()
    feed["data"]["btc"]["score"] = "invalid"
    markets = reference.get_market_overview()
    assert markets["source"]["mode"] == "cached"
    assert markets["assets"][0]["score"] == 0


def test_fund_universe_holdings_fees_and_independent_score():
    client = TestClient(app)
    active = client.get("/api/v1/funds?kind=active").json()
    passive = client.get("/api/v1/funds?kind=passive").json()
    assert (len(active), len(passive)) == (23, 16)
    assert len({f["code"] for f in active + passive}) == 39
    fund = next(f for f in active if f["code"] == "017436")
    assert fund["purchase_limit"] == 200
    assert fund["excess_return_pct"] == 2.91
    assert len(fund["holdings_top10"]["holdings"]) == 10
    assert fund["holdings_full"]["holdings"]
    assert fund["fees"]["management"] == .015
    assert client.get("/api/v1/funds/017436").json() == fund
    score = client.get("/api/v1/fund-market-score").json()
    assert (score["score"], score["multiplier"]) == (47, .8)
    assert sum(d["weight"] for d in score["dimensions"].values()) == 100


def test_portfolios_preserve_original_allocations_and_weighted_growth():
    rows = reference.get_portfolios()
    assert len(rows) == 10
    assert rows[0]["allocation"] == {"VTI": 30, "TLT": 40, "IEF": 15, "GSG": 7.5, "GLD": 7.5}
    assert rows[0]["allocation_labels"]["VTI"] == "美国股票 (VTI)"
    assert rows[0]["ticker"].split(" · ")[0] == "VTI 30%"
    assert [row["risk_level"] for row in rows] == [2, 1, 3, 3, 3, 3, 3, 4, 5, 3]
    assert rows[6]["allocation"] == {"SPY": 25, "VB": 25, "VXUS": 25, "SHY": 25}
    assert rows[8]["annualized_pct"] == 12.41
    assert rows[8]["final_value"] == 32010
    for row in rows:
        assert sum(row["allocation"].values()) == 100
        assert len(row["yearly"]) == 9
        assert row["stress_tests"]


def test_hs300_recovered_thresholds_and_cashflows():
    assert hs300_valuation(9, 1) == 92
    assert hs300_valuation(14, 1.8) == 65
    assert hs300_multiplier(79) == 1.5
    assert hs300_multiplier(80) == 2
    assert hs300_multiplier(10) == .5  # published browser setting clamps min to 0.5
    assert hs300_multiplier(10, minimum=.2) == .2
    rows = hs300_history([{"date": "2020-01-31", "price": 100, "pe": 9, "pb": 1},
                          {"date": "2020-02-29", "price": 50, "pe": 9, "pb": 1}])
    assert rows[-1]["invested"] == 400
    assert rows[-1]["value"] == 300
    assert rows[-1]["regular_value"] == 150
    assert rows[-1]["buyhold_value"] == 100
    assert rows[-1]["return_pct"] == -25


def test_network_failure_keeps_snapshot_provenance(monkeypatch):
    monkeypatch.delenv("REFERENCE_OFFLINE")
    def fail(*args, **kwargs):
        raise httpx.ConnectError("test outage")
    monkeypatch.setattr(reference.httpx, "get", fail)
    payload, source = reference._load("btc_score")
    assert payload["data"]["totalScore"] == 82
    assert source["mode"] == "snapshot"
    assert source["error"] == "test outage"
    assert source["captured_at"]


def test_invalid_live_payload_cannot_replace_valid_snapshot(monkeypatch):
    monkeypatch.delenv("REFERENCE_OFFLINE")
    monkeypatch.setattr(reference.httpx, "get", lambda *a, **k: httpx.Response(200, json={"success": False}, request=httpx.Request("GET", a[0])))
    payload, source = reference._load("gold_score")
    assert payload["data"]["totalScore"] == 60
    assert source["mode"] == "snapshot"
    assert not list(reference.CACHE_DIR.glob("*.json"))


def test_incomplete_success_response_is_not_accepted():
    assert not reference._valid_payload("btc_score", {"success": True, "data": {}})
    assert not reference._valid_payload("gold_history", {"success": True, "data": "not history"})
    assert not reference._valid_payload("markets", {"success": True, "data": {}})
    assert reference._valid_payload("markets", {"success": True, "data": {"hs300": None}})


def test_capture_parser_accepts_data_and_rejects_executable_expressions():
    script = Path(__file__).resolve().parents[2] / "scripts" / "sync_reference.py"
    spec = importlib.util.spec_from_file_location("sync_reference", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.Literal("{name:'测试', /* comment */ weights: [30, 7.5, null,], active:true}").value() == {
        "name": "测试", "weights": [30, 7.5, None], "active": True}
    for expression in ("fetch('https://example.com')", "[alert(1)]", "{x: process.exit()}"):
        with pytest.raises(ValueError):
            module.Literal(expression).value()


def test_unknown_routes_and_invalid_query_are_not_silent_successes():
    client = TestClient(app)
    for path in ("/assets/unknown", "/funds/unknown", "/portfolios/unknown"):
        assert client.get("/api/v1" + path).status_code == 404
    assert client.get("/api/v1/funds?kind=invalid").status_code == 422
