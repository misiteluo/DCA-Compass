import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { Drawer } from "../components/Widgets";
import { PieChart } from "../components/Charts";
import SourceNote from "../components/SourceNote";
import type { FundMarketScore, Fund, Holdings } from "../types";

const fmt = (v: number | null | undefined, suffix = "") =>
  v == null ? "--" : `${v}${suffix}`;

type SortKey = "scale_yi" | "total_return_pct" | "annualized_pct" | "daily_change_pct" | "max_drawdown_pct";

const percent = (value: number | null | undefined, digits?: number) =>
  value == null ? "--" : `${value > 0 ? "+" : ""}${digits == null ? value : value.toFixed(digits)}%`;

const changeClass = (value: number | null | undefined) =>
  value == null || value === 0 ? undefined : value > 0 ? "up" : "down";

function purchaseLimit(value: number | null) {
  if (value == null) return "--";
  if (value === 0) return "暂停申购";
  if (value >= 100000000) return "无限额";
  if (value >= 10000) return `¥${(value / 10000).toFixed(0)}万`;
  return `¥${value.toLocaleString("zh-CN")}`;
}

const performancePeriods = {
  "1m": "近1月", "3m": "近3月", "6m": "近6月", "1y": "近1年", "3y": "近3年", "5y": "近5年", all: "成立以来",
};

export default function Funds() {
  const [kind, setKind] = useState<"active" | "passive">("active");
  const [funds, setFunds] = useState<Fund[]>([]);
  const [banner, setBanner] = useState<FundMarketScore | null>(null);
  const [sort, setSort] = useState<{ key: SortKey; asc: boolean } | null>({ key: "scale_yi", asc: false });
  const [detail, setDetail] = useState<Fund | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [scoreError, setScoreError] = useState(false);

  useEffect(() => {
    let active = true;
    api.fundMarketScore().then((d) => { if (active) setBanner(d); }).catch(() => { if (active) setScoreError(true); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true); setError(""); setFunds([]);
    api.funds(kind).then((d) => { if (active) setFunds(d); }).catch((e) => { if (active) setError(String(e)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [kind]);

  const sorted = useMemo(() => {
    if (!sort) return funds;
    return [...funds].sort((x, y) => {
      const a = x[sort.key];
      const b = y[sort.key];
      if (a == null && b == null) return 0;
      if (a == null) return 1;
      if (b == null) return -1;
      return (a - b) * (sort.asc ? 1 : -1);
    });
  }, [funds, sort]);

  const head = (label: string, key: SortKey) => (
    <th scope="col" aria-sort={sort?.key === key ? (sort.asc ? "ascending" : "descending") : undefined}>
      <button type="button" className="sort-button" onClick={() => setSort({ key, asc: sort?.key === key && !sort.asc })}>
        {label}{sort?.key === key && <span aria-hidden="true">{sort.asc ? " ↑" : " ↓"}</span>}
      </button>
    </th>
  );

  const listLabel = kind === "active" ? "主动型基金" : "被动型基金";

  return (
    <div className="wrap">
      <section>
        <h2>国内投资美股基金定投推荐（支付宝可买）</h2>
        <div className="card">
          美股市场定投评分<span className="score" style={{ fontSize: 22 }}> {banner?.score ?? "--"}</span>
          {banner?.status && `（${banner.status}）`} · 定投倍数 <b>{banner?.multiplier != null ? `${banner.multiplier.toFixed(2)}x` : "--"}</b>
          <p>{banner?.strategy}</p>
          <div className="kv"><span>参考指数</span><b>纳指100</b></div>
          {banner?.computedAt && <div className="kv"><span>评分日期</span><b>{banner.computedAt.slice(0, 10)}</b></div>}
          {Object.entries(banner?.dimensions ?? {}).map(([key, d]) => <div className="kv" key={key}><span>{d.label} · 权重 {d.weight}%</span><b>{d.score}</b></div>)}
          {scoreError && <p role="alert">市场评分加载失败。</p>}
          <SourceNote source={banner?.source} />
        </div>
      </section>

      <section>
        {error && <p role="alert">数据加载失败：{error}</p>}
        <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
          <button type="button" aria-pressed={kind === "active"} className={`btn${kind === "active" ? " on" : ""}`} onClick={() => setKind("active")}>主动型</button>
          <button type="button" aria-pressed={kind === "passive"} className={`btn${kind === "passive" ? " on" : ""}`} onClick={() => setKind("passive")}>被动型（纳指100指数）</button>
        </div>
        {loading && <p role="status">正在加载基金…</p>}
        {!loading && !error && (
          <div className="table-scroll" role="region" aria-label={listLabel} tabIndex={0}><table aria-label={listLabel}>
            <thead><tr>
              <th scope="col"><button type="button" className="sort-button" aria-label="基金名称（恢复默认顺序）" onClick={() => setSort(null)}>基金名称</button></th>
              {head("规模(亿)", "scale_yi")}<th scope="col">成立时间</th>
              {head("成立至今", "total_return_pct")}{head("年化收益", "annualized_pct")}
              <th scope="col">纳指100同期</th><th scope="col">超额收益</th>
              {head("当日涨跌", "daily_change_pct")}{head("最大回撤", "max_drawdown_pct")}<th scope="col">日限额</th>
            </tr></thead>
            <tbody>
              {sorted.map((f) => (
                <tr key={f.code} className="clickable" onClick={() => setDetail(f)}>
                  <th scope="row" style={{ color: "inherit" }}>
                    <button type="button" className="sort-button" onClick={(e) => { e.stopPropagation(); setDetail(f); }}>{f.name}</button>
                    <div className="muted">{f.code}</div>
                  </th>
                  <td>{fmt(f.scale_yi)}</td><td>{f.inception ?? "--"}</td>
                  <td className={changeClass(f.total_return_pct)}>{percent(f.total_return_pct)}</td>
                  <td className={changeClass(f.annualized_pct)}>{percent(f.annualized_pct)}</td>
                  <td>{percent(f.benchmark_cagr_pct)}</td>
                  <td className={changeClass(f.excess_return_pct)}>
                    {percent(f.excess_return_pct, 2)}{f.beat_benchmark != null && ` ${f.beat_benchmark ? "跑赢" : "跑输"}`}
                  </td>
                  <td className={changeClass(f.daily_change_pct)}>{percent(f.daily_change_pct, 2)}</td>
                  <td className={changeClass(f.max_drawdown_pct)}>{percent(f.max_drawdown_pct)}</td>
                  <td>{purchaseLimit(f.purchase_limit)}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
        {!loading && !error && <p className="muted">已收录 {funds.length} 只基金。点击名称查看持仓与详情，限额按数据源披露展示。</p>}
        <SourceNote source={funds[0]?.source} />
      </section>

      {detail && (
        <Drawer title={`${detail.name}（${detail.code}）`} onClose={() => setDetail(null)}>
          <SourceNote source={detail.source} />
          <div className="kv"><span>当日涨跌</span><b className={changeClass(detail.daily_change_pct)}>{percent(detail.daily_change_pct, 2)}</b></div>
          <div className="kv"><span>规模</span><b>{fmt(detail.scale_yi, " 亿")}</b></div>
          <div className="kv"><span>成立时间</span><b>{detail.inception ?? "--"}</b></div>
          <div className="kv"><span>成立至今</span><b className={changeClass(detail.total_return_pct)}>{percent(detail.total_return_pct)}</b></div>
          <div className="kv"><span>年化收益</span><b className={changeClass(detail.annualized_pct)}>{percent(detail.annualized_pct)}</b></div>
          <div className="kv"><span>最大回撤</span><b className={changeClass(detail.max_drawdown_pct)}>{percent(detail.max_drawdown_pct)}</b></div>
          <div className="kv"><span>支付宝日买入限额</span><b>{purchaseLimit(detail.purchase_limit)}</b></div>
          <h4>业绩表现</h4>
          {Object.entries(performancePeriods).map(([key, label]) => (
            <div className="kv" key={key}><span>{label}</span><b className={changeClass(detail.returns?.[key])}>{percent(detail.returns?.[key])}</b></div>
          ))}
          <h4>风险指标</h4>
          <div className="kv"><span>夏普比率</span><b>{fmt(detail.risk?.sharpe)}</b></div>
          <div className="kv"><span>年化波动率</span><b>{fmt(detail.risk?.volatility_pct, "%")}</b></div>
          <div className="kv"><span>贝塔系数</span><b>{fmt(detail.risk?.beta)}</b></div>
          <div className="kv"><span>阿尔法</span><b>{fmt(detail.risk?.alpha, "%")}</b></div>
          <HoldingsPanel title="最新季报前十大持仓" data={detail.holdings_top10} chart />
          <HoldingsPanel title="完整持仓明细" data={detail.holdings_full} />
          <h4>资产配置（占净值比）</h4>
          {detail.allocation
            ? Object.entries(detail.allocation).map(([k, v]) => (
              <div className="kv" key={k}><span>{k}</span><b>{fmt(v, "%")}</b></div>))
            : <p className="muted">--</p>}
          <h4>基金经理</h4>
          <p>{detail.manager ? `${detail.manager.name}（任职 ${detail.manager.tenure} 至今）` : "--"}</p>
          <p className="muted">{detail.manager?.desc}</p>
          <h4>费率</h4>
          {detail.fees ? <>
            {Object.entries({ purchase: "申购费率", redemption: "赎回费率", management: "管理费率（年）", custodian: "托管费率（年）", sales: "销售服务费（年）" }).map(([key, label]) => {
              const rate = detail.fees?.[key] ?? 0;
              const zeroLabel = key === "sales" ? "无" : key === "purchase" || key === "redemption" ? "免费" : null;
              return <div className="kv" key={key}><span>{label}</span><b>{rate === 0 && zeroLabel ? zeroLabel : `${(rate * 100).toFixed(2)}%`}</b></div>;
            })}
            <div className="kv"><span>综合运作费率（年）</span><b>{(["management", "custodian", "sales"].reduce((sum, key) => sum + (detail.fees?.[key] ?? 0), 0) * 100).toFixed(2)}%</b></div>
          </> : <p>暂无费率数据</p>}
        </Drawer>
      )}
    </div>
  );
}

function HoldingsPanel({ title, data, chart = false }: { title: string; data?: Holdings | null; chart?: boolean }) {
  if (!data?.holdings?.length) return null;
  const total = data.holdings.reduce((sum, h) => sum + h.weight, 0);
  return <><h4>{title}</h4>
    <p className="muted">{[data.quarter, data.reportDate].filter(Boolean).join(" · ")}</p>
    {chart ? <PieChart data={data.holdings.slice(0, 10).map((h) => ({ name: h.name, value: h.weight }))} /> : (
      <p className="muted">{data.holdings.length} 只 · 总占比 {total.toFixed(2)}% · 重仓股（&gt;5%）{data.holdings.filter((h) => h.weight > 5).length} 只</p>
    )}
    <table aria-label={title}><thead><tr><th scope="col">证券</th><th scope="col">权重</th><th scope="col">当日涨跌</th></tr></thead>
      <tbody>{data.holdings.map((h, i) => <tr key={`${h.code}-${i}`}>
        <th scope="row">{h.name}<div className="muted">{h.code}</div></th><td>{h.weight.toFixed(2)}%</td>
        <td className={changeClass(h.dailyChange)}>{percent(h.dailyChange, 2)}</td>
      </tr>)}</tbody>
    </table>
  </>;
}
