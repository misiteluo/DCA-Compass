import math

from app.services import indicators as ind
from app.services.backtest import _score_series
from app.services.scoring import BUILDERS, composite, multiplier


def test_multiplier_btc_piecewise():
    assert multiplier("btc", 0) == 0.10
    assert multiplier("btc", 50) == 0.80
    assert multiplier("btc", 85) == 1.95
    assert multiplier("btc", 100) == 3.00
    assert multiplier("btc", 65) == round(0.80 + (1.20 - 0.80) * 15 / 20, 2)


def test_multiplier_gold_steps():
    assert multiplier("gold", 10) == 0.5
    assert multiplier("gold", 40) == 0.7
    assert multiplier("gold", 50) == 1.0
    assert multiplier("gold", 60) == 1.5
    assert multiplier("gold", 90) == 3.0


def test_multiplier_ndx_spx_hs300():
    assert multiplier("nasdaq", 0) == 0.0
    assert multiplier("nasdaq", 100) == 2.50
    assert multiplier("sp500", 70) == 1.63
    assert multiplier("hs300", 25) == 0.2
    assert multiplier("hs300", 100) == round(min(2.0, 0.2 + 75 * 0.024), 2)


def test_multiplier_monotonic():
    for asset in ("btc", "gold", "nasdaq", "sp500", "hs300"):
        vals = [multiplier(asset, s) for s in range(0, 101, 5)]
        assert vals == sorted(vals)


def test_percentile_scoring_bounds():
    series = list(range(1, 201))
    s = ind.percentile_score(series, low_is_high=True)
    assert s is not None and 0 <= s <= 100
    assert ind.percentile_score([1.0] * 10, low_is_high=True) is None  # too short


def test_percentile_direction():
    rising = [float(i) for i in range(100)]  # last value is the max
    assert ind.percentile_score(rising, low_is_high=True) < 5
    assert ind.percentile_score(rising, low_is_high=False) > 95


def _fake_ctx():
    closes = [100 + 10 * math.sin(i / 25) + i * 0.02 for i in range(900)]
    return {"closes": closes, "dates": [f"202{i//365}-01-01" for i in range(900)],
            "prices": [{"date": "2020-01-01", "close": c, "volume": 1e6} for c in closes],
            "vix": [20.0] * 100, "dxy": [100.0] * 100, "tnx": [4.0] * 100,
            "fgi": [], "tips": [], "will5000": [], "gdp": [],
            "mvrv": [], "issuance": [], "hashrate": []}


def test_weights_sum_100_and_renormalize():
    ctx = _fake_ctx()
    for asset, builder in BUILDERS.items():
        dims = builder(ctx)
        total = sum(d["weight"] for d in dims)
        assert total == 100, f"{asset} weights sum {total}"
        score, dims2 = composite([dict(d) for d in dims])
        if score is not None:
            eff = sum(d["weight_effective"] for d in dims2 if d["score"] is not None)
            assert abs(eff - 100) < 1.0, f"{asset} effective weights {eff}"


def test_backtest_no_lookahead():
    closes = [100.0] * 300 + [50.0] * 300 + [200.0] * 300
    scores_a = _score_series(closes)
    truncated = _score_series(closes[:600])
    # scores at indices present in both runs must be identical
    for i, v in truncated.items():
        if i in scores_a:
            assert scores_a[i] == v


def test_max_drawdown():
    assert ind.max_drawdown([100, 120, 60, 90]) == -50.0
    assert ind.max_drawdown([1, 2, 3]) == 0.0
