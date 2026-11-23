import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { Drawer } from "../components/Widgets";
import type { AssetSummary, Fund } from "../types";

const fmt = (v: number | null | undefined, suffix = "") =>
  v == null ? "--" : `${v}${suffix}`;

type SortKey = keyof Fund;

export default function Funds() {
  const [kind, setKind] = useState<"active" | "passive">("active");
  const [funds, setFunds] = useState<Fund[]>([]);
  const [banner, setBanner] = useState<AssetSummary | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("total_return_pct");
  const [asc, setAsc] = useState(false);
  const [detail, setDetail] = useState<Fund | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.assets().then((list) => setBanner(list.find((a) => a.id === "nasdaq") ?? null)).catch(() => undefined);
  }, []);

  useEffect(() => {
    setLoading(true);
    api.funds(kind).then(setFunds).catch(() => setFunds([])).finally(() => setLoading(false));
  }, [kind]);

  const sorted = useMemo(() => {
    const rows = [...funds];
    rows.sort((x, y) => {
      const a = x[sortKey] as number | string | null;
      const b = y[sortKey] as number | string | null;
      if (a == null) return 1;
      if (b == null) return -1;
      return (a < b ? -1 : a > b ? 1 : 0) * (asc ? 1 : -1);
    });
    return rows;
  }, [funds, sortKey, asc]);

  const head = (label: string, key: SortKey) => (
    <th className="sortable" onClick={() => { setSortKey(key); setAsc(sortKey === key ? !asc : false); }}>
      {label}{sortKey === key ? (asc ? " ↑" : " ↓") : ""}
    </th>
  );

  const open = (code: string) => {
    setDetail({ code, name: "加载中…", kind, status: "loading" } as Fund);
    api.fund(code).then(setDetail).catch(() => setDetail(null));
  };

  return (
    <div className="wrap">
      <section>
        <h2>国内投资美股基金定投推荐（支付宝可买）</h2>
        <div className="card">
          美股市场定投评分（纳斯达克100）<span className="score" style={{ fontSize: 22 }}> {banner?.score ?? "--"}</span>
          （{banner?.zone ?? ""}）· 定投倍数 <b>{banner?.multiplier != null ? `${banner.multiplier}x` : "--"}</b>
          <span className="muted"> · 数据来源：东方财富（基金净值）/ 本站评分引擎 · {banner?.date ?? ""}</span>
        </div>
      </section>

      <section>
        <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
          <button className={`btn${kind === "active" ? " on" : ""}`} onClick={() => setKind("active")}>主动型</button>
          <button className={`btn${kind === "passive" ? " on" : ""}`} onClick={() => setKind("passive")}>被动型（纳指100指数）</button>
        </div>
        {loading ? <p>加载中…（首次需逐只抓取净值）</p> : (
          <table>
            <thead><tr>
              {head("基金名称", "name")}{head("规模(亿)", "scale_yi")}{head("成立时间", "inception")}
              {head("成立至今", "total_return_pct")}{head("年化收益", "annualized_pct")}
              {head("当日涨跌", "daily_change_pct")}{head("最大回撤", "max_drawdown_pct")}{head("日限额", "purchase_limit")}
            </tr></thead>
            <tbody>
              {sorted.map((f) => (
                <tr key={f.code} className="clickable" onClick={() => open(f.code)}>
                  <td>{f.name}<div className="muted">{f.code}</div></td>
                  <td>{fmt(f.scale_yi)}</td><td>{f.inception ?? "--"}</td>
                  <td>{fmt(f.total_return_pct, "%")}</td><td>{fmt(f.annualized_pct, "%")}</td>
                  <td>{fmt(f.daily_change_pct, "%")}</td><td>{fmt(f.max_drawdown_pct, "%")}</td>
                  <td>{f.purchase_limit != null ? `¥${f.purchase_limit}` : "--"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="muted">点击任意一行查看详情。日限额随基金公司公告每日变化，本站数据源不提供该字段时显示 --。</p>
      </section>

      {detail && (
        <Drawer title={`${detail.name}（${detail.code}）`} onClose={() => setDetail(null)}>
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
          <div className="kv"><span>贝塔 / 阿尔法</span><b>--（{detail.risk?.note ?? "待接入"}）</b></div>
          <h4>资产配置（占净值比）</h4>
          {detail.allocation
            ? Object.entries(detail.allocation).map(([k, v]) => (
              <div className="kv" key={k}><span>{k}</span><b>{v}%</b></div>))
            : <p className="muted">--</p>}
          <h4>基金经理</h4>
          <p>{detail.manager ? `${detail.manager.name}（从业 ${detail.manager.tenure}）` : "--"}</p>
          <h4>费率</h4>
          <p className="muted">本站数据源未提供完整费率表，请以基金公司公告为准。</p>
        </Drawer>
      )}
    </div>
  );
}
