"""Capture public reference data; parse literals as data, never execute site scripts.

Run with the project's Python: python scripts/sync_reference.py [--from-dir DIR]
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "backend" / "reference"
ASSETS = ("btc", "gold", "nasdaq", "sp500", "hs300")
ENDPOINTS = {f"{a}_score": f"/{a}/api/score" for a in ASSETS[:4]}
ENDPOINTS.update({
    "markets": "/api/v2/markets",
    "nasdaq_12d": "/nasdaq/api/score-12d",
    "hs300_score": "/hs300/api/hs300/dimensions",
    "hs300_spot": "/hs300/api/hs300/spot",
    "fund_score": "/us-fund-holdings/api/score",
    "hs300_trades": "/hs300/api/robot/trades",
    **{f"{a}_history": f"/{a}/api/history?days=5000" for a in ASSETS[:4]},
})


class Literal:
    """Only JS object/array/string/number literals; rejects expressions and calls."""
    token = re.compile(r'\s+|//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|[\w$]+|.', re.S)

    def __init__(self, source):
        self.tokens = (m.group() for m in self.token.finditer(source)
                       if not m.group().isspace() and not m.group().startswith(("//", "/*")))
        self.current = next(self.tokens)

    def take(self):
        value = self.current
        self.current = next(self.tokens, "")
        return value

    def value(self):
        token = self.take()
        if token in ("[", "{"):
            out = [] if token == "[" else {}
            end = "]" if token == "[" else "}"
            while self.current != end:
                if token == "[":
                    out.append(self.value())
                else:
                    key = self.take()
                    if key.startswith(("'", '"')):
                        key = self.string(key)
                    if self.take() != ":":
                        raise ValueError("Expected literal property")
                    out[key] = self.value()
                if self.current == ",":
                    self.take()
                elif self.current != end:
                    raise ValueError("Not a literal")
            self.take()
            return out
        if token.startswith(("'", '"')):
            return self.string(token)
        if token in ("true", "false", "null"):
            return {"true": True, "false": False, "null": None}[token]
        if re.fullmatch(r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?', token):
            return float(token) if any(c in token for c in ".eE") else int(token)
        raise ValueError(f"Rejected non-literal token: {token}")

    @staticmethod
    def string(token):
        # JSON strings dominate embedded data; JS single quotes only need common escapes.
        if token.startswith('"'):
            return json.loads(token)
        return re.sub(r"\\(['\\/])", r"\1", token[1:-1]).replace("\\n", "\n").replace("\\t", "\t")


def constant(source, name, default=None):
    match = re.search(r"\b(?:const|let|var)\s+" + re.escape(name) + r"\s*=\s*", source)
    return Literal(source[match.end():]).value() if match else default


class Node:
    def __init__(self, tag="root", attrs=(), parent=None):
        self.tag, self.attrs, self.parent, self.children = tag, dict(attrs), parent, []

    def text(self):
        if self.tag in ("script", "style"):
            return ""
        return re.sub(r"\s+", " ", " ".join(c if isinstance(c, str) else c.text() for c in self.children)).strip()

    def find(self, predicate):
        return [n for c in self.children if isinstance(c, Node)
                for n in ([c] if predicate(c) else []) + c.find(predicate)]


class DOM(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = self.node = Node()
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        child = Node(tag, attrs, self.node)
        self.node.children.append(child)
        if tag not in ("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"):
            self.node = child

    def handle_endtag(self, tag):
        node = self.node
        while node.parent and node.tag != tag:
            node = node.parent
        if node.parent:
            self.node = node.parent

    def handle_data(self, data):
        self.node.children.append(data)


def report(html):
    dom = DOM(html).root
    tables = []
    for table in dom.find(lambda n: n.tag == "table"):
        rows = [[cell.text() for cell in row.find(lambda n: n.tag in ("td", "th"))]
                for row in table.find(lambda n: n.tag == "tr")]
        rows = [row for row in rows if any(row)]
        if not rows:
            continue
        node, before = table, []
        while node.parent and not before:
            siblings = [n for n in node.parent.children if isinstance(n, Node)]
            before = siblings[:siblings.index(node)]
            node = node.parent
        tables.append({"title": before[-1].text()[:160] if before else "数据明细", "rows": rows})
    def is_metric(n):
        return bool({"d-mrow", "d-metric"} & set(n.attrs.get("class", "").split()))

    metrics = [n.text() for n in dom.find(is_metric) if not n.find(is_metric)]
    # Preserve strategy instructions as content, without importing the reference HTML or scripts.
    strategy = []
    for heading in dom.find(lambda n: n.tag == "h2"):
        if any(t in heading.text() for t in ("策略说明", "智能定投系统", "策略详情")):
            siblings = [c for c in heading.parent.parent.children if isinstance(c, Node)]
            for sibling in siblings[siblings.index(heading.parent) + 1:]:
                if sibling.tag in ("footer", "script") or "section-header" in sibling.attrs.get("class", ""):
                    break
                blocks = [c for c in sibling.children if isinstance(c, Node)] or [sibling]
                strategy.extend(b.text() for b in blocks if b.text())
    narrative = [n.text() for n in dom.find(lambda n: "d-panel" in n.attrs.get("class", "").split())
                 if not n.find(lambda c: c.tag == "table")]
    result = {"tables": tables, "metrics": metrics, "strategy": strategy, "narrative": narrative}
    yearly_highlights = []
    for n in dom.find(lambda n: n.tag in ("div", "span") and all(isinstance(c, str) for c in n.children)):
        label = n.text()
        if re.fullmatch(r"(?:最佳|最差)年份 · (?:Best Year|Worst Year|\d{4})|正收益年份", label):
            group = n.parent.parent if re.search(r"\d{4}$", label) else n.parent
            yearly_highlights.append(group.text())
    if yearly_highlights:
        result["yearly_highlights"] = yearly_highlights
    return result


def static_heatmap(html):
    section = html.split("<!-- 5. 月度热力图 -->", 1)[-1].split("<!-- 6. 风险指标 -->", 1)[0]
    rows = re.split(r"<!-- (\d{4}) -->", section)[1:]
    monthly = {}
    for year, block in zip(rows[::2], rows[1::2]):
        values = re.findall(r">\s*([-+]\d+(?:\.\d+)?)%\s*</div>", block)
        if len(values) == 12:
            monthly[year] = [float(value) for value in values]
    return monthly


def asset_report(asset, html):
    r = report(html)
    scatter = re.findall(r"label:\s*['\"]([^'\"]+)['\"],\s*data:\s*\[\{\s*x:\s*([-\d.]+),\s*y:\s*([-\d.]+)\s*\}\]", html)
    r["risk_return"] = [{"name": name, "drawdown": float(x), "return_pct": float(y)} for name, x, y in scatter]
    for label, key in (("总投入", "capital_invested"), ("累计收益", "capital_profit"), ("总回报率 (%)", "total_returns")):
        match = re.search(r"label:\s*['\"]" + re.escape(label) + r"['\"],\s*data:\s*(\[[^\]]+\])", html)
        if match:
            r[key] = Literal(match[1]).value()
    for name in ("years", "returns", "strategyReturns", "dcaReturns", "standardReturns", "bhReturns", "buyholdReturns",
                 "growthLabels", "strategyValue", "standardValue", "bhValue", "dates", "drawdowns", "monthlyData", "bins",
                 "counts", "DIM12_CONFIG", "bullBearNodes"):
        try:
            value = constant(html, name)
        except ValueError:
            continue
        if value is not None:
            r[name] = value
    if asset == "nasdaq":
        comparison = html.split("function initNasdaqAnnualReturnsChart()", 1)[-1]
        r["comparison_years"] = constant(comparison, "years")
    if asset == "sp500":
        r["monthly_heatmap"] = static_heatmap(html)
    return r


def extract(pages):
    funds = constant(pages["us-fund-holdings"], "FUND_DATA")
    lazy = pages["lazy"]
    portfolios = constant(lazy, "D")
    etf = constant(lazy, "ETF")
    annual = dict(re.findall(r'(\w+):\s*wRET\((\[.*?\])\)', lazy))
    for p in portfolios:
        weights = Literal(annual[p["key"]]).value()
        p["annual"] = [sum(etf.get(t, etf["VTI"])[i] * w / 100 for t, w in weights) for i in range(9)]
    data = {"captured_at": datetime.now(timezone.utc).isoformat(), "funds": funds, "portfolios": portfolios,
            "portfolio_stress": constant(lazy, "DD"), "reports": {}}
    for asset in ASSETS:
        data["reports"][asset] = asset_report(asset, pages[asset])
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-dir", type=Path)
    args = parser.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    pages = {}
    names = (*ASSETS, "lazy", "us-fund-holdings")
    with httpx.Client(timeout=35, follow_redirects=True) as client:
        for name in names:
            if args.from_dir:
                pages[name] = (args.from_dir / f"{name}.html").read_text(encoding="utf-8")
            else:
                response = client.get(f"https://btcdca.me/{name}/")
                response.raise_for_status()
                pages[name] = response.text
        dataset = extract(pages)
        (DEST / "site.json").write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")

        def capture(item):
            key, path = item
            response = client.get("https://btcdca.me" + path)
            response.raise_for_status()
            payload = response.json()
            if not payload.get("success"):
                raise ValueError(f"Reference returned failure: {key}")
            envelope = {"captured_at": datetime.now(timezone.utc).isoformat(), "url": "https://btcdca.me" + path, "payload": payload}
            (DEST / f"{key}.json").write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
            return key

        with ThreadPoolExecutor(max_workers=5) as pool:
            for key, future in zip(ENDPOINTS, [pool.submit(capture, item) for item in ENDPOINTS.items()]):
                try:
                    print(f"captured {future.result()}")
                except (httpx.HTTPError, ValueError) as error:
                    print(f"unavailable {key}: {error}")


if __name__ == "__main__":
    main()
