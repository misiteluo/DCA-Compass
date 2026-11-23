#!/usr/bin/env python3
"""定投罗盘 DCA Compass — data pipeline + site generator (stdlib only).
Fetch daily prices (Yahoo chart API, Stooq fallback) -> percentile scoring
-> weekly DCA backtest -> data.json -> static HTML site.
Regenerate:  python3 pipeline/build_data.py
"""
import csv, io, json, math, os, sys, time, urllib.parse, urllib.request
from bisect import insort
from datetime import date, datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
CACHE = os.path.join(ROOT, "data_cache")
os.makedirs(SITE, exist_ok=True); os.makedirs(CACHE, exist_ok=True)
START = "2015-01-01"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

# ---------------- fetch ----------------
def fetch_yahoo(sym):
    p1 = int(datetime(2015,1,1,tzinfo=timezone.utc).timestamp())
    p2 = int(time.time()) + 86400
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym, safe='')}?period1={p1}&period2={p2}&interval=1d"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        d = json.load(r)
    res = (d.get("chart") or {}).get("result") or []
    if not res: raise ValueError("yahoo: empty result")
    r0 = res[0]; ts = r0.get("timestamp") or []
    q = (r0.get("indicators") or {}).get("quote") or [{}]
    close = (q[0].get("close") or [])
    adj = ((r0.get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose") or close
    rows = []
    for t, c, a in zip(ts, close, adj):
        v = a if a is not None else c
        if v is None: continue
        dt = datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
        if dt >= START: rows.append((dt, float(v)))
    if len(rows) < 100: raise ValueError(f"yahoo: only {len(rows)} rows")
    return rows

def fetch_stooq(sym):
    url = f"https://stooq.com/q/d/l/?s={urllib.parse.quote(sym)}&i=d"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        text = r.read().decode("utf-8", "replace")
    rows = []
    for row in csv.DictReader(io.StringIO(text)):
        if row.get("Date") and row.get("Close") and row["Date"] >= START:
            try: rows.append((row["Date"], float(row["Close"])))
            except ValueError: pass
    if len(rows) < 100: raise ValueError(f"stooq: only {len(rows)} rows")
    return rows

def fetch(asset_id, tries):
    """tries: list of (source, symbol). Cached per asset for the day."""
    cache = os.path.join(CACHE, f"{asset_id}.json")
    if os.path.exists(cache) and datetime.fromtimestamp(os.path.getmtime(cache)).strftime("%Y-%m-%d") == date.today().isoformat():
        d = json.load(open(cache)); return d["rows"], d["source"], d["symbol"]
    errs = []
    for src, sym in tries:
        try:
            rows = fetch_yahoo(sym) if src == "yahoo" else fetch_stooq(sym)
            json.dump({"rows": rows, "source": src, "symbol": sym}, open(cache, "w"))
            return rows, src, sym
        except Exception as e:
            errs.append(f"{src}:{sym}: {e}")
    raise RuntimeError("; ".join(errs))

# ---------------- indicators ----------------
def ema(vals, n):
    k = 2/(n+1); out = []; e = None
    for v in vals:
        e = v if e is None else v*k + e*(1-k); out.append(e)
    return out

def indicators(closes, dates, is_btc=False):
    """Return dict name -> list aligned with closes (None until enough history)."""
    n = len(closes)
    rets = [None] + [closes[i]/closes[i-1]-1 for i in range(1, n)]
    def sma(i, w): return sum(closes[i-w+1:i+1])/w if i >= w-1 else None
    e12, e26 = ema(closes, 12), ema(closes, 26)
    macd = [a-b for a, b in zip(e12, e26)]; sig = ema(macd, 9)
    ind = {k: [None]*n for k in ("ma200","ma50","rsi","boll","dd52","vol20","pos3y","macd")}
    if is_btc: ind["ahr"] = [None]*n
    gains = [0.0]*n; losses = [0.0]*n
    for i in range(1, n):
        d = closes[i]-closes[i-1]; gains[i] = max(d, 0); losses[i] = max(-d, 0)
    for i in range(n):
        if i >= 199: ind["ma200"][i] = closes[i]/sma(i,200)-1
        if i >= 49: ind["ma50"][i] = closes[i]/sma(i,50)-1
        if i >= 14:
            g = sum(gains[i-13:i+1])/14; l = sum(losses[i-13:i+1])/14
            ind["rsi"][i] = 100.0 if l == 0 else 100 - 100/(1+g/l)
        if i >= 19:
            m = sma(i,20); sd = math.sqrt(sum((x-m)**2 for x in closes[i-19:i+1])/20)
            ind["boll"][i] = 0.5 if sd == 0 else (closes[i]-(m-2*sd))/(4*sd)
        if i >= 60:
            hi = max(closes[max(0,i-251):i+1]); ind["dd52"][i] = closes[i]/hi-1
        if i >= 20:
            r = rets[i-19:i+1]; m = sum(r)/20
            ind["vol20"][i] = math.sqrt(sum((x-m)**2 for x in r)/20)
        if i >= 60:
            w = closes[max(0,i-755):i+1]; lo, hi = min(w), max(w)
            ind["pos3y"][i] = 0.5 if hi == lo else (closes[i]-lo)/(hi-lo)
        if i >= 35: ind["macd"][i] = (macd[i]-sig[i])/closes[i]
        if is_btc and i >= 199:
            days = (datetime.strptime(dates[i], "%Y-%m-%d") - datetime(2009,1,3)).days
            model = 10**(5.84*math.log10(max(days,1)) - 17.01)
            ind["ahr"][i] = (closes[i]/sma(i,200)) * (closes[i]/model)
    return ind

# dimension spec: key, label, weight (generic), inverted? (low raw = high score)
DIMS = [
    ("ma200", "MA200 偏离度", 18, True, lambda v: f"{v*100:+.2f}%"),
    ("ma50",  "MA50 偏离度",  10, True, lambda v: f"{v*100:+.2f}%"),
    ("rsi",   "RSI(14)",      15, True, lambda v: f"{v:.1f}"),
    ("boll",  "布林带 %B",    12, True, lambda v: f"{v:.2f}"),
    ("dd52",  "距52周高点回撤", 15, True, lambda v: f"{v*100:.1f}%"),
    ("vol20", "20日波动率",    8, False, lambda v: f"{v*100:.2f}%"),
    ("pos3y", "3年价格位置",  12, True, lambda v: f"{v*100:.1f}%"),
    ("macd",  "MACD 柱/价格", 10, True, lambda v: f"{v*100:.3f}%"),
]
BTC_EXTRA = ("ahr", "AHR999 风格指数", 14, True, lambda v: f"{v:.3f}")
BTC_WEIGHTS = {"ma200":14,"ma50":8,"rsi":13,"boll":10,"dd52":13,"vol20":7,"pos3y":11,"macd":10,"ahr":14}

def pct_rank(sorted_vals, v):
    from bisect import bisect_right
    return bisect_right(sorted_vals, v)/len(sorted_vals) if sorted_vals else 0.5

def score_at(ind, idx, weights):
    """Score at day idx using only indicator history up to idx (expanding percentile)."""
    total = 0.0; wsum = 0.0; dims = {}
    for key, label, _w, inv, fmt in _dim_list(weights):
        hist = sorted(x for x in ind[key][:idx+1] if x is not None)
        cur = ind[key][idx]
        if cur is None or len(hist) < 60: continue
        p = pct_rank(hist, cur)
        s = round(100*(1-p) if inv else 100*p, 1)
        dims[key] = {"label": label, "raw": cur, "raw_fmt": fmt(cur), "score": s, "weight": weights[key]}
        total += s*weights[key]; wsum += weights[key]
    if wsum == 0: return 50.0, dims
    return round(total/wsum, 1), dims  # weights sum 100 when all dims available; renormalise only if early/missing

def _dim_list(weights):
    out = []
    for d in DIMS: out.append(d)
    if "ahr" in weights: out.append(BTC_EXTRA)
    return out

POINTS = [(0,0.2),(30,0.5),(50,0.8),(70,1.2),(85,1.95),(100,3.0)]
def multiplier(score):
    for (x0,y0),(x1,y1) in zip(POINTS, POINTS[1:]):
        if score <= x1: return round(y0 + (y1-y0)*(score-x0)/(x1-x0), 2)
    return 3.0
def zone(score):
    return "高估" if score < 30 else "偏高估" if score < 50 else "合理" if score < 70 else "低估" if score < 85 else "极度低估"

# ---------------- backtest ----------------
def backtest(rows, ind, weights):
    """Weekly DCA: first trading day of each ISO week, base 100/week."""
    closes = [c for _, c in rows]; dates = [d for d, _ in rows]
    weeks = []
    seen = set()
    for i, d in enumerate(dates):
        y, w, _ = datetime.strptime(d, "%Y-%m-%d").isocalendar()
        if (y, w) not in seen: seen.add((y, w)); weeks.append(i)
    base = 100.0
    lump = base*len(weeks)
    bh_shares = lump/closes[weeks[0]]
    s_sh = r_sh = 0.0; s_inv = 0.0
    curve = []; yearly = {}
    prev_year_val = 0.0; year_inv = {}
    for i in weeks:
        sc, _ = score_at(ind, i, weights)
        amt = base*multiplier(sc)
        s_sh += amt/closes[i]; s_inv += amt
        r_sh += base/closes[i]
        year_inv[dates[i][:4]] = year_inv.get(dates[i][:4], 0) + amt
        curve.append((dates[i], s_sh*closes[i], r_sh*closes[i], bh_shares*closes[i], s_inv))
    for yr in sorted(year_inv):
        vals = [c for c in curve if c[0][:4] == yr]
        end_val = vals[-1][1]
        yearly[yr] = round((end_val/(prev_year_val + year_inv[yr]) - 1)*100, 2) if (prev_year_val + year_inv[yr]) else 0.0
        prev_year_val = end_val
    last = closes[-1]
    def stats(inv, final):
        yrs = (datetime.strptime(dates[-1], "%Y-%m-%d") - datetime.strptime(dates[weeks[0]], "%Y-%m-%d")).days/365.25
        return {"invested": round(inv,2), "final": round(final,2),
                "return_pct": round((final/inv-1)*100, 2),
                "cagr_pct": round(((final/inv)**(1/yrs)-1)*100, 2) if inv > 0 and final > 0 else 0.0}
    vals = [c[1] for c in curve]; peak = -1; mdd = 0.0
    for v in vals:
        peak = max(peak, v); mdd = min(mdd, v/peak-1) if peak > 0 else 0.0
    return {"freq": "weekly", "base_per_week": base, "weeks": len(weeks),
            "strategy": stats(s_inv, s_sh*last), "regular": stats(lump, r_sh*last),
            "buyhold": stats(lump, bh_shares*last), "max_drawdown_pct": round(mdd*100, 2),
            "yearly": yearly, "curve": [[c[0], round(c[1],2), round(c[2],2), round(c[3],2)] for c in curve],
            "start": dates[weeks[0]], "end": dates[-1]}

# ---------------- lazy portfolios ----------------
PORTFOLIOS = [
    ("全天候组合", {"VTI":30,"TLT":40,"IEF":15,"GLD":7.5,"DBC":7.5}, "季度再平衡", "达里奥式风险平价思路，股债商品分散"),
    ("永久组合", {"VTI":25,"TLT":25,"GLD":25,"SHY":25}, "年度再平衡（偏离>5%时）", "四等分：增长/繁荣/通缩/通胀各一份"),
    ("经典 60/40", {"VTI":60,"BND":40}, "年度再平衡", "最经典的股债平衡组合"),
    ("三基金组合", {"VTI":34,"VXUS":33,"BND":33}, "年度再平衡", "美股+国际股+美债，一站式全球分散"),
    ("核心四资产", {"VTI":38,"VXUS":27,"VNQ":10,"BND":25}, "年度再平衡", "三基金基础上加房地产 REIT"),
    ("巴菲特 90/10", {"VOO":90,"SHY":10}, "年度再平衡", "90% 标普500 + 10% 短期国债"),
]
def lazy_backtests():
    tickers = sorted({t for _, alloc, _, _ in PORTFOLIOS for t in alloc})
    series = {}
    for t in tickers:
        try:
            rows, _, _ = fetch(f"lazy-{t}", [("yahoo", t), ("stooq", f"{t.lower()}.us")])
            series[t] = dict(rows)
        except Exception as e:
            print(f"lazy {t}: {e}", file=sys.stderr)
    out = []
    for name, alloc, rule, desc in PORTFOLIOS:
        item = {"name": name, "alloc": alloc, "rule": rule, "desc": desc, "stats": None}
        if all(t in series for t in alloc):
            cal = sorted(d for d in series[next(iter(alloc))] if d >= "2017-01-01")
            px = {}
            for t in alloc:
                last = None; px[t] = {}
                for d in cal:
                    last = series[t].get(d, last); px[t][d] = last
            if all(px[t][cal[0]] for t in alloc):
                shares = {t: 10000*alloc[t]/100/px[t][cal[0]] for t in alloc}
                vals = []; qseen = set()
                for d in cal:
                    yq = d[:4] + "Q" + str((int(d[5:7])-1)//3)
                    if yq not in qseen and d != cal[0]:
                        qseen.add(yq); tot = sum(shares[t]*px[t][d] for t in alloc)
                        shares = {t: tot*alloc[t]/100/px[t][d] for t in alloc}
                    vals.append(sum(shares[t]*px[t][d] for t in alloc))
                rets = [vals[i]/vals[i-1]-1 for i in range(1, len(vals))]
                yrs = (datetime.strptime(cal[-1], "%Y-%m-%d") - datetime.strptime(cal[0], "%Y-%m-%d")).days/365.25
                mean = sum(rets)/len(rets); var = sum((r-mean)**2 for r in rets)/len(rets)
                peak = -1; mdd = 0.0
                for v in vals:
                    peak = max(peak, v); mdd = min(mdd, v/peak-1)
                item["stats"] = {"start": cal[0], "end": cal[-1], "final": round(vals[-1],2),
                    "cagr_pct": round(((vals[-1]/10000)**(1/yrs)-1)*100, 2),
                    "vol_pct": round(math.sqrt(var)*math.sqrt(252)*100, 2),
                    "maxdd_pct": round(mdd*100, 2),
                    "sharpe": round(mean/math.sqrt(var)*math.sqrt(252), 2) if var > 0 else 0.0}
        out.append(item)
    return out

# ---------------- assets ----------------
ASSETS = [
    ("btc", "比特币 BTC", "BTC", [("yahoo","BTC-USD"),("stooq","btcusd")], True),
    ("gold", "黄金 Gold", "GC=F 黄金期货", [("yahoo","GC=F"),("yahoo","GLD"),("stooq","gld.us")], False),
    ("nasdaq", "纳斯达克100", "QQQ（纳指100 ETF 代理）", [("yahoo","QQQ"),("stooq","qqq.us")], False),
    ("sp500", "标普500", "SPY（标普500 ETF 代理）", [("yahoo","SPY"),("stooq","spy.us")], False),
    ("hs300", "沪深300", "510300（沪深300 ETF 代理）", [("yahoo","510300.SS")], False),
]
FUNDS = [
    ("纳斯达克100", "广发纳斯达克100ETF联接(QDII)A", "270042"), ("纳斯达克100", "广发纳斯达克100ETF联接(QDII)C", "006479"),
    ("纳斯达克100", "国泰纳斯达克100指数(QDII)", "160213"), ("纳斯达克100", "华夏纳斯达克100ETF联接(QDII)A", "015299"),
    ("纳斯达克100", "博时纳斯达克100指数发起(QDII)A", "016055"), ("纳斯达克100", "华安纳斯达克100指数(QDII)A", "040046"),
    ("纳斯达克100", "大成纳斯达克100指数(QDII)", "000834"), ("纳斯达克100", "国泰纳斯达克100ETF（场内）", "513100"),
    ("纳斯达克100", "广发纳斯达克100ETF（场内）", "159941"), ("纳斯达克100", "华夏纳斯达克100ETF（场内）", "513300"),
    ("标普500", "博时标普500ETF联接(QDII)A", "050025"), ("标普500", "易方达标普500指数(QDII)A", "161125"),
    ("标普500", "博时标普500ETF（场内）", "513500"),
]

def main():
    data = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "assets": [], "multiplier_points": POINTS,
            "funds_note": "基金清单（净值数据待接入）", "funds": [{"index": a, "name": b, "code": c} for a, b, c in FUNDS]}
    report = []
    for aid, name, sym_label, tries, is_btc in ASSETS:
        item = {"id": aid, "name": name, "symbol_label": sym_label, "available": False}
        try:
            rows, src, sym = fetch(aid, tries)
        except Exception as e:
            item["error"] = str(e); data["assets"].append(item); report.append((name, f"FAILED {e}")); continue
        closes = [c for _, c in rows]; dates = [d for d, _ in rows]
        ind = indicators(closes, dates, is_btc)
        weights = BTC_WEIGHTS if is_btc else {k: w for k, _, w, _, _ in DIMS}
        assert sum(weights.values()) == 100, weights
        score, dims = score_at(ind, len(closes)-1, weights)
        mult = multiplier(score)
        bt = backtest(rows, ind, weights)
        # downsampled price+MA200 for chart
        ma200 = [None]*len(closes)
        for i in range(199, len(closes)): ma200[i] = sum(closes[i-199:i+1])/200
        step = max(1, len(closes)//400)
        price_series = [[dates[i], closes[i], round(ma200[i],4) if ma200[i] else None] for i in range(0, len(closes), step)]
        item.update({"available": True, "source": src, "symbol": sym, "rows": len(rows),
            "start": dates[0], "end": dates[-1], "price": closes[-1],
            "change_pct": round((closes[-1]/closes[-2]-1)*100, 2),
            "score": score, "multiplier": mult, "zone": zone(score),
            "dims": [dims[k] for k in weights if k in dims], "backtest": bt, "price_series": price_series})
        data["assets"].append(item); report.append((name, f"{src}:{sym} rows={len(rows)} {dates[0]}..{dates[-1]} score={score} x{mult}"))
        print(report[-1][1])
    data["lazy"] = lazy_backtests()
    json.dump(data, open(os.path.join(SITE, "data.json"), "w"), ensure_ascii=False)
    json.dump(data, open(os.path.join(ROOT, "data.json"), "w"), ensure_ascii=False)
    build_site(data)
    print("OK -> site/")

# ---------------- site ----------------
CSS = """<style>
:root{--bg:#0d1117;--card:#161b22;--line:#30363d;--tx:#e6edf3;--mut:#8b949e;--acc:#f0b90b;--up:#3fb950;--dn:#f85149}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif}
a{color:var(--acc);text-decoration:none}header,footer{max-width:1080px;margin:0 auto;padding:18px 16px}
nav a{margin-right:14px;color:var(--tx)}main{max-width:1080px;margin:0 auto;padding:0 16px 40px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:12px 0}
.big{font-size:42px;font-weight:700}.score{color:var(--acc)}table{border-collapse:collapse;width:100%;font-size:14px}
td,th{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left}.mut{color:var(--mut);font-size:13px}
.bar{height:10px;background:#21262d;border-radius:5px}.bar i{display:block;height:10px;background:var(--acc);border-radius:5px}
</style>"""
NAV = """<header><div style="font-size:22px;font-weight:700">🧭 定投罗盘 <span style="color:var(--mut);font-size:14px">DCA Compass</span></div>
<nav style="margin-top:8px"><a href="index.html">首页</a><a href="btc.html">BTC</a><a href="gold.html">黄金</a><a href="nasdaq.html">纳指100</a><a href="sp500.html">标普500</a><a href="hs300.html">沪深300</a><a href="lazy.html">懒人组合</a><a href="funds.html">美股基金</a></nav></header>"""
FOOT = """<footer class="mut">定投罗盘 DCA Compass · 数据来自公开行情源，评分基于历史百分位，仅供学习参考。<b>本站不构成投资建议</b>，定投有风险，决策请独立判断。</footer>"""

def svg_lines(series_list, colors, w=1000, h=300):
    """series_list: list of list of (x_idx, value) already aligned by position; log scale."""
    allv = [math.log10(v) for s in series_list for _, v in s if v and v > 0]
    if not allv: return ""
    lo, hi = min(allv), max(allv); rng = (hi-lo) or 1
    n = max(len(s) for s in series_list)
    out = [f'<svg viewBox="0 0 {w} {h}" style="width:100%;background:#0d1117;border:1px solid var(--line);border-radius:8px">']
    for s, col in zip(series_list, colors):
        pts = " ".join(f"{i/(n-1)*w:.1f},{h-8-(math.log10(v)-lo)/rng*(h-16):.1f}" for i, v in s if v and v > 0)
        out.append(f'<polyline fill="none" stroke="{col}" stroke-width="1.6" points="{pts}"/>')
    out.append("</svg>"); return "".join(out)

def build_site(data):
    by_id = {a["id"]: a for a in data["assets"]}
    # homepage
    cards = ""
    for a in data["assets"]:
        if a["available"]:
            cards += f"""<div class="card"><h3><a href="{a['id']}.html">{a['name']}</a></h3>
            <div class="mut">{a['symbol_label']} · {a['end']}</div>
            <div>价格 <b>{a['price']:,.2f}</b> <span style="color:{'var(--up)' if a['change_pct']>=0 else 'var(--dn)'}">{a['change_pct']:+.2f}%</span></div>
            <div class="big score">{a['score']:.0f} 分</div><div>定投倍数 <b>{a['multiplier']}x</b> · 区间：{a['zone']}</div></div>"""
        else:
            cards += f"""<div class="card"><h3>{a['name']}</h3><div class="mut">数据暂不可用（{a.get('error','')}）</div></div>"""
    method = """<div class="card"><h3>方法论：评分怎么算</h3><ol>
    <li><b>数据采集</b>：公开行情源日线价格（2015 年至今），单一 data.json 作为全站唯一数据源，首页与资产页数字必然一致。</li>
    <li><b>指标计算</b>：每个资产计算 MA200/MA50 偏离、RSI、布林带 %B、52 周回撤、20 日波动率、3 年价格位置、MACD 等维度（BTC 另加 AHR999 风格维度）。</li>
    <li><b>百分位归一化</b>：每个维度取当前值在自身全部历史中的百分位，映射为 0-100 分——越便宜/机会越大分越高。</li>
    <li><b>加权评分</b>：各维度按固定权重加权求和，权重合计严格 100%。</li>
    <li><b>倍数映射</b>：全站统一分段线性映射：0分→0.2x，30→0.5x，50→0.8x，70→1.2x，85→1.95x，100→3.0x。页面显示的倍数就是该公式代入显示分数的结果。</li>
    <li><b>回测</b>：每周定投一次，策略定投金额 = 基准×当日倍数（分数只用当日及之前数据，无未来函数），与普通定投、一次性买入持有对比。</li></ol></div>"""
    html = f"<!DOCTYPE html><html lang='zh'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>定投罗盘 DCA Compass</title>{CSS}</head><body>{NAV}<main><p class='mut'>五资产智能定投评分 · 更新于 {data['generated_at']} · 分数越高 = 历史位置越便宜 = 本周建议倍数越大</p><div class='grid'>{cards}</div>{method}</main>{FOOT}</body></html>"
    open(os.path.join(SITE, "index.html"), "w").write(html)
    # asset pages
    for a in data["assets"]:
        if not a["available"]: continue
        bt = a["backtest"]
        dim_rows = "".join(f"<tr><td>{d['label']}</td><td>{d['raw_fmt']}</td><td>{d['score']:.1f}</td><td>{d['weight']}%</td><td style='width:30%'><div class='bar'><i style='width:{d['score']}%'></i></div></td></tr>" for d in a["dims"])
        dim_bars = [(i, d["score"]) for i, d in enumerate(a["dims"])]
        price_s = [(i, p[1]) for i, p in enumerate(a["price_series"])]
        ma_s = [(i, p[2]) for i, p in enumerate(a["price_series"]) if p[2]]
        curve = bt["curve"]
        growth = [[(i, c[1]) for i, c in enumerate(curve)], [(i, c[2]) for i, c in enumerate(curve)], [(i, c[3]) for i, c in enumerate(curve)]]
        yr_rows = "".join(f"<tr><td>{y}</td><td style='color:{'var(--up)' if v>=0 else 'var(--dn)'}'>{v:+.2f}%</td></tr>" for y, v in bt["yearly"].items())
        map_rows = "".join(f"<tr><td>{x} 分</td><td>{y}x</td></tr>" for x, y in POINTS)
        st, rg, bh = bt["strategy"], bt["regular"], bt["buyhold"]
        page = f"""<!DOCTYPE html><html lang='zh'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{a['name']} · 定投罗盘</title>{CSS}</head><body>{NAV}<main>
        <h2>{a['name']}</h2><p class='mut'>{a['symbol_label']} · 数据源 {a['source']}:{a['symbol']} · {a['start']} ~ {a['end']}（{a['rows']} 个交易日）</p>
        <div class="card"><div>最新价格 <b style="font-size:22px">{a['price']:,.2f}</b> <span style="color:{'var(--up)' if a['change_pct']>=0 else 'var(--dn)'}">{a['change_pct']:+.2f}%</span></div>
        <div class="big score">{a['score']:.1f} 分 · {a['zone']}</div><div style="font-size:20px">本周定投倍数 <b>{a['multiplier']}x</b>（基准金额 × {a['multiplier']}）</div>
        <div class="bar" style="margin-top:10px"><i style="width:{a['score']}%"></i></div><div class="mut">0 高估 ———— 50 合理 ———— 100 极度低估</div></div>
        <div class="card"><h3>维度明细（原始值 → 百分位分数 × 权重，合计 100%）</h3><table><tr><th>维度</th><th>原始值</th><th>分数</th><th>权重</th><th></th></tr>{dim_rows}</table></div>
        <div class="card"><h3>价格与 MA200</h3>{svg_lines([price_s, ma_s], ['#e6edf3','#f0b90b'])}<p class="mut">白=价格，黄=MA200（对数轴）</p></div>
        <div class="card"><h3>回测（{bt['start']} ~ {bt['end']}，每周定投，基准 100/周，共 {bt['weeks']} 周）</h3>
        <table><tr><th>策略</th><th>总投入</th><th>期末市值</th><th>总收益</th><th>年化(CAGR*)</th></tr>
        <tr><td>策略定投（按倍数）</td><td>{st['invested']:,.0f}</td><td>{st['final']:,.0f}</td><td>{st['return_pct']:+.2f}%</td><td>{st['cagr_pct']:.2f}%</td></tr>
        <tr><td>普通定投（固定金额）</td><td>{rg['invested']:,.0f}</td><td>{rg['final']:,.0f}</td><td>{rg['return_pct']:+.2f}%</td><td>{rg['cagr_pct']:.2f}%</td></tr>
        <tr><td>一次性买入持有</td><td>{bh['invested']:,.0f}</td><td>{bh['final']:,.0f}</td><td>{bh['return_pct']:+.2f}%</td><td>{bh['cagr_pct']:.2f}%</td></tr></table>
        <p class="mut">策略定投组合最大回撤 {bt['max_drawdown_pct']:.2f}% 。*CAGR 按 期末市值/总投入 的资金倍数年化计算，与一次性投资的 CAGR 口径略有不同，仅作横向参考。</p>
        <h4>资金增长曲线（对数轴：黄=策略定投，绿=普通定投，红=买入持有）</h4>{svg_lines(growth, ['#f0b90b','#3fb950','#f85149'])}</div>
        <div class="card"><h3>策略定投年度收益</h3><table><tr><th>年份</th><th>收益</th></tr>{yr_rows}</table><p class="mut">年度收益 = 年末组合市值 /（年初市值 + 当年投入）− 1。</p></div>
        <div class="card"><h3>统一倍数映射表（全站一致）</h3><table><tr><th>综合分数</th><th>定投倍数</th></tr>{map_rows}</table><p class="mut">区间：0-30 高估 · 30-50 偏高估 · 50-70 合理 · 70-85 低估 · 85-100 极度低估，区间内分段线性插值。</p></div>
        </main>{FOOT}</body></html>"""
        open(os.path.join(SITE, f"{a['id']}.html"), "w").write(page)
    # lazy page
    lcards = ""
    for p in data["lazy"]:
        alloc = " · ".join(f"{t} {w}%" for t, w in p["alloc"].items())
        if p["stats"]:
            s = p["stats"]; stats = f"<table><tr><td>回测区间</td><td>{s['start']} ~ {s['end']}（初始 10,000，季度再平衡）</td></tr><tr><td>期末市值</td><td>{s['final']:,.0f}</td></tr><tr><td>年化收益</td><td>{s['cagr_pct']:.2f}%</td></tr><tr><td>年化波动</td><td>{s['vol_pct']:.2f}%</td></tr><tr><td>最大回撤</td><td>{s['maxdd_pct']:.2f}%</td></tr><tr><td>夏普(无风险利率=0)</td><td>{s['sharpe']}</td></tr></table>"
        else:
            stats = "<p class='mut'>回测统计待接入（成分 ETF 行情未取全，不展示估算数字）</p>"
        lcards += f"<div class='card'><h3>{p['name']}</h3><p>{p['desc']}</p><p class='mut'>配置：{alloc}<br>再平衡：{p['rule']}</p>{stats}</div>"
    open(os.path.join(SITE, "lazy.html"), "w").write(f"<!DOCTYPE html><html lang='zh'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>懒人组合 · 定投罗盘</title>{CSS}</head><body>{NAV}<main><h2>懒人组合</h2><p class='mut'>经典资产配置组合，行情与五资产页同源（Yahoo），2017 年起回测。</p>{lcards}</main>{FOOT}</body></html>")
    # funds page
    frows = "".join(f"<tr><td>{f['index']}</td><td>{f['name']}</td><td>{f['code']}</td></tr>" for f in data["funds"])
    open(os.path.join(SITE, "funds.html"), "w").write(f"<!DOCTYPE html><html lang='zh'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>美股基金 · 定投罗盘</title>{CSS}</head><body>{NAV}<main><h2>美股基金清单</h2><div class='card'><p><b>基金清单（净值数据待接入）</b>：以下为国内可买的纳指100 / 标普500 QDII 指数基金清单（代码经公开资料核对），净值、收益、限额等实时数据尚未接入，申购前请以基金公司公告为准。本站不展示任何估算净值。</p><table><tr><th>跟踪指数</th><th>基金名称</th><th>代码</th></tr>{frows}</table></div></main>{FOOT}</body></html>")

if __name__ == "__main__":
    main()
