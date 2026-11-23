"""Rules recovered from the reference's public HS300 browser calculator."""
from __future__ import annotations

import math


def hs300_valuation(pe, pb, peg=1.5, roe=25):
    def below(value, limits, scores):
        return next((score for limit, score in zip(limits, scores) if value < limit), 5)

    pe_score = below(pe, (10, 12, 14, 16, 18, 20, 22, 24, 26), (95, 85, 75, 65, 55, 45, 35, 25, 15))
    pb_score = below(pb, (1.1, 1.3, 1.5, 1.8, 2.1, 2.4, 2.7, 3.0, 3.3), (95, 85, 75, 65, 55, 45, 35, 25, 15))
    peg_score = next((s for limit, s in ((1, 95), (1.3, 85), (1.6, 75), (2, 65), (2.5, 55)) if peg <= limit), 45)
    roe_score = next((s for limit, s in ((25, 95), (22, 85), (18, 75), (15, 65)) if roe >= limit), 55)
    # JavaScript Math.round uses ties toward +infinity, unlike Python round.
    return math.floor(pe_score * .5 + pb_score * .3 + peg_score * .15 + roe_score * .05 + .5)


def hs300_multiplier(score, minimum=.5, maximum=2):
    value = next((m for limit, m in ((80, 2), (65, 1.5), (50, 1), (35, .5), (20, .3)) if score >= limit), .2)
    return max(minimum, min(maximum, value))


def hs300_history(monthly):
    shares = regular_shares = invested = regular_invested = 0.0
    bh_invested = len(monthly) * 100
    bh_shares = bh_invested / monthly[0]["price"] if monthly else 0
    rows = []
    for item in monthly:
        score = hs300_valuation(item["pe"], item["pb"])
        mult = hs300_multiplier(score)
        amount = 100 * mult
        invested += amount
        regular_invested += 100
        shares += amount / item["price"]
        regular_shares += 100 / item["price"]
        rows.append({**item, "score": score, "multiplier": mult, "amount": amount,
                     "invested": invested, "value": shares * item["price"],
                     "regular_invested": regular_invested, "regular_value": regular_shares * item["price"],
                     "buyhold_invested": bh_invested, "buyhold_value": bh_shares * item["price"],
                     "return_pct": (shares * item["price"] / invested - 1) * 100})
    return rows
