import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import { Drawer } from "../components/Widgets";
import { PieChart } from "../components/Charts";
import SourceNote from "../components/SourceNote";
import type { FundMarketScore, Fund, Holdings } from "../types";

const fmt = (v: number | null | undefined, suffix = "") =>
  v == null ? "--" : `${v}${suffix}`;

type SortKey = keyof Fund;

export default function Funds() {
  const [kind, setKind] = useState<"active" | "passive">("active");
  const [funds, setFunds] = useState<Fund[]>([]);
  const [banner, setBanner] = useState<FundMarketScore | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("scale_yi");
  const [asc, setAsc] = useState(false);
  const [detail, setDetail] = useState<Fund | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const request = useRef(0);

  useEffect(() => {
    let active = true;
    api.fundMarketScore().then((d) => { if (active) setBanner(d); }).catch((e) => { if (active) setError(String(e)); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true); setError(""); setFunds([]);
    api.funds(kind).then((d) => { if (active) setFunds(d); }).catch((e) => { if (active) setError(String(e)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [kind]);

  const sorted = useMemo(() => {
    const rows = [...funds];
    rows.sort((x, y) => {
      const a = x[sortKey] as number | string | null;
      const b = y[sortKey] as number | string | null;
      if (a == null && b == null) return 0;
      if (a == null) return 1;
      if (b == null) return -1;
      return (a < b ? -1 : a > b ? 1 : 0) * (asc ? 1 : -1);
    });
    return rows;
  }, [funds, sortKey, asc]);

  const head = (label: string, key: SortKey) => (
    <th aria-sort={sortKey === key ? (asc ? "ascending" : "descending") : "none"}>
      <button className="sort-button" onClick={() => { setSortKey(key); setAsc(sortKey === key ? !asc : false); }}>{label}{sortKey === key ? (asc ? " ↑" : " ↓") : ""}</button>
    </th>
  );

  const open = (code: string) => {
    const token = ++request.current;
    setDetail(funds.find((f) => f.code === code) ?? null);
    api.fund(code).then((f) => { if (request.current === token) setDetail(f); }).catch((e) => { if (request.current === token) setError(String(e)); });
  };
  const close = () => { request.current++; setDetail(null); };

  return (
    <div className="wrap">
      <section>
        <h2>国内投资美股基金定投推荐（支付宝可买）</h2>
        <div className="card">
          美股市场定投评分<span className="score" style={{ fontSize: 22 }}> {banner?.score ?? "--"}</span>
          （{banner?.status ?? ""}）· 定投倍数 <b>{banner?.multiplier != null ? `${banner.multiplier}x` : "--"}</b>
          <p>{banner?.strategy}</p>
          {Object.entries(banner?.dimensions ?? {}).map(([key, d]) => <div className="kv" key={key}><span>{d.label} · 权重 {d.weight}%</span><b>{d.score}</b></div>)}
          <SourceNote source={banner?.source} />
        </div>
      </section>

      <section>
        {error && <p role="alert">数据加载失败：{error}</p>}
        <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
          <button className={`btn${kind === "active" ? " on" : ""}`} onClick={() => setKind("active")}>主动型</button>
          <button className={`btn${kind === "passive" ? " on" : ""}`} onClick={() => setKind("passive")}>被动型（纳指100指数）</button>
        </div>
        {loading ? <p>加载中…（首次需逐只抓取净值）</p> : (
          <div className="table-scroll"><table>
            <thead><tr>
              {head("基金名称", "name")}{head("规模(亿)", "scale_yi")}{head("成立时间", "inception")}
              {head("成立至今", "total_return_pct")}{head("年化收益", "annualized_pct")}
              {head("纳指100同期", "benchmark_cagr_pct")}{head("超额收益", "excess_return_pct")}
              {head("当日涨跌", "daily_change_pct")}{head("最大回撤", "max_drawdown_pct")}{head("日限额", "purchase_limit")}
            </tr></thead>
            <tbody>
              {sorted.map((f) => (
                <tr key={f.code} className="clickable" onClick={() => open(f.code)}>
                  <td><button className="sort-button" onClick={(e) => { e.stopPropagation(); open(f.code); }}>{f.name}</button><div className="muted">{f.code}</div></td>
                  <td>{fmt(f.scale_yi)}</td><td>{f.inception ?? "--"}</td>
                  <td>{fmt(f.total_return_pct, "%")}</td><td>{fmt(f.annualized_pct, "%")}</td>
                  <td>{fmt(f.benchmark_cagr_pct, "%")}</td><td className={(f.excess_return_pct ?? 0) >= 0 ? "up" : "down"}>{fmt(f.excess_return_pct, "%")}</td>
                  <td>{fmt(f.daily_change_pct, "%")}</td><td>{fmt(f.max_drawdown_pct, "%")}</td>
                  <td>{f.purchase_limit == null ? "--" : f.purchase_limit >= 100000000 ? "无限额" : f.purchase_limit === 0 ? "暂停申购" : `¥${f.purchase_limit.toLocaleString()}`}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
        <p className="muted">已收录 {funds.length} 只基金。点击名称查看持仓与详情；限额按数据源披露展示。</p>
        <SourceNote source={funds[0]?.source} />
      </section>

      {detail && (
        <Drawer title={`${detail.name}（${detail.code}）`} onClose={close}>
          <SourceNote source={detail.source} />
          <div className="kv"><span>当日涨跌</span><b>{fmt(detail.daily_change_pct, "%")}</b></div>
          <div className="kv"><span>规模</span><b>{fmt(detail.scale_yi, " 亿")}</b></div>
          <div className="kv"><span>成立时间</span><b>{detail.inception ?? "--"}</b></div>
          <div className="kv"><span>成立至今</span><b>{fmt(detail.total_return_pct, "%")}</b></div>
          <div className="kv"><span>年化收益</span><b>{fmt(detail.annualized_pct, "%")}</b></div>
          <div className="kv"><span>最大回撤</span><b>{fmt(detail.max_drawdown_pct, "%")}</b></div>
          <h4>业绩表现</h4>
          {detail.returns && Object.entries({ "近1月": "1m", "近3月": "3m", "近6月": "6m", "近1年": "1y", "近3年": "3y", "近5年": "5y" }).map(([label, k]) => (
            <div className="kv" key={k}><span>{label}</span><b>{fmt(detail.returns?.[k], "%")}</b></div>
          ))}
          <h4>风险指标</h4>
          <div className="kv"><span>夏普比率</span><b>{fmt(detail.risk?.sharpe)}</b></div>
          <div className="kv"><span>年化波动率</span><b>{fmt(detail.risk?.volatility_pct, "%")}</b></div>
          <div className="kv"><span>贝塔 / 阿尔法</span><b>{fmt(detail.risk?.beta)} / {fmt(detail.risk?.alpha, "%")}</b></div>
          <HoldingsPanel title="最新季报前十大持仓" data={detail.holdings_top10} chart />
          <HoldingsPanel title="完整持仓明细" data={detail.holdings_full} />
          <h4>资产配置（占净值比）</h4>
          {detail.allocation
            ? Object.entries(detail.allocation).map(([k, v]) => (
              <div className="kv" key={k}><span>{k}</span><b>{v}%</b></div>))
            : <p className="muted">--</p>}
          <h4>基金经理</h4>
          <p>{detail.manager ? `${detail.manager.name}（任职 ${detail.manager.tenure} 至今）` : "--"}</p>
          <p className="muted">{detail.manager?.desc}</p>
          <h4>费率</h4>
          {detail.fees ? <>
            {Object.entries({ purchase: "申购费率", redemption: "赎回费率", management: "管理费率（年）", custodian: "托管费率（年）", sales: "销售服务费（年）" }).map(([key, label]) => <div className="kv" key={key}><span>{label}</span><b>{((detail.fees?.[key] ?? 0) * 100).toFixed(2)}%</b></div>)}
            <div className="kv"><span>综合运作费率（年）</span><b>{(["management", "custodian", "sales"].reduce((sum, key) => sum + (detail.fees?.[key] ?? 0), 0) * 100).toFixed(2)}%</b></div>
          </> : <p>暂无费率数据</p>}
        </Drawer>
      )}
    </div>
  );
}

function HoldingsPanel({ title, data, chart = false }: { title: string; data?: Holdings | null; chart?: boolean }) {
  if (!data?.holdings?.length) return <><h4>{title}</h4><p className="muted">暂无披露数据</p></>;
  const total = data.holdings.reduce((sum, h) => sum + h.weight, 0);
  return <><h4>{title} · {data.quarter ?? data.reportDate}</h4>
    {chart && <PieChart data={data.holdings.map((h) => ({ name: h.name, value: h.weight }))} />}
    <p className="muted">{data.holdings.length} 只 · 总占比 {total.toFixed(2)}% · 重仓股（&gt;5%）{data.holdings.filter((h) => h.weight > 5).length} 只</p>
    <table><thead><tr><th>证券</th><th>权重</th><th>当日涨跌</th></tr></thead><tbody>{data.holdings.map((h, i) => <tr key={`${h.code}-${i}`}><td>{h.name}<div className="muted">{h.code}</div></td><td>{h.weight}%</td><td>{fmt(h.dailyChange, "%")}</td></tr>)}</tbody></table>
  </>;
}
