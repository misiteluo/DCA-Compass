import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { BarChart, LineChart, PieChart } from "../components/Charts";
import SourceNote from "../components/SourceNote";
import type { Portfolio } from "../types";

export function LazyList() {
  const [list, setList] = useState<Portfolio[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { api.portfolios().then(setList).catch((e) => setError(String(e))); }, []);
  return (
    <div className="wrap">
      <section>
        <h2>全球十大懒人投资组合</h2>
        <p className="muted">2017–2025 年历史报告 · 组合配置、风险指标及年度加权收益按参考站公布口径展示。</p>
        {error && <p role="alert">加载失败：{error}</p>}
        {!error && !list.length && <p role="status">正在加载组合…</p>}
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(250px,1fr))" }}>
          {list.map((p, i) => (
            <Link key={p.id} to={`/lazy/${p.id}`} className="card">
              <h3>NO.{String(i + 1).padStart(2, "0")} {p.name}</h3>
              <div className="kv"><span>年化收益</span><b>{p.annualized_pct ?? "--"}%</b></div>
              <div className="kv"><span>波动率</span><b>{p.volatility_pct ?? "--"}%</b></div>
              <div className="kv"><span>最大回撤</span><b>{p.max_drawdown_pct ?? "--"}%</b></div>
              <div className="kv"><span>夏普比率</span><b>{p.sharpe ?? "--"}</b></div>
              <div className="kv"><span>风险等级</span><b>{p.risk}</b></div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

export function PortfolioDetail() {
  const { id = "" } = useParams();
  const [p, setP] = useState<Portfolio | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { let active = true; setP(null); setError(""); api.portfolio(id).then((d) => { if (active) setP(d); }).catch((e) => { if (active) setError(String(e)); }); return () => { active = false; }; }, [id]);
  if (!p) return <div className="wrap"><p role="status">{error || "加载中…"}</p></div>;
  return (
    <div className="wrap">
      <p><Link to="/lazy">← 返回所有组合</Link></p>
      <section style={{ marginTop: 8 }}>
        <h2>{p.name}</h2>
        <p>{p.name_en} · {p.founder}</p><p className="muted">{p.philosophy}</p>
        <SourceNote source={p.source} />
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))" }}>
          <div className="card">
            <h3>持仓配置</h3>
            <PieChart data={Object.entries(p.allocation).map(([name, value]) => ({ name, value }))} />
          </div>
          <div className="card">
            <h3>回测概览（{p.period}）</h3>
            <div className="kv"><span>初始资金</span><b>${p.initial?.toLocaleString()}</b></div>
            <div className="kv"><span>期末价值</span><b>${p.final_value?.toLocaleString()}</b></div>
            <div className="kv"><span>年化收益</span><b>{p.annualized_pct}%</b></div>
            <div className="kv"><span>波动率</span><b>{p.volatility_pct}%</b></div>
            <div className="kv"><span>最大回撤</span><b>{p.max_drawdown_pct}%</b></div>
            <div className="kv"><span>夏普比率</span><b>{p.sharpe}</b></div>
            <div className="kv"><span>索提诺比率</span><b>{p.sortino}</b></div>
            <div className="kv"><span>Beta / Alpha</span><b>{p.beta} / {p.alpha}%</b></div>
            <div className="kv"><span>R²</span><b>{p.r2}%</b></div>
            <div className="kv"><span>最好 / 最差年份</span><b>{p.best}% / {p.worst}%</b></div>
            <p className="muted">{p.note}</p>
          </div>
        </div>
      </section>
      <section>
        <h2>组合增长（初始 $10,000）</h2>
        <div className="card"><LineChart dates={p.growth_curve?.map((c) => c.date) ?? []} series={[{ name: p.name, data: p.growth_curve?.map((c) => c.value) ?? [], color: "#f0b90b" }]} /></div>
        <h2>年度回报</h2>
        <div className="card"><BarChart cats={Object.keys(p.yearly ?? {})} series={[{ name: "年度回报 %", data: Object.values(p.yearly ?? {}), color: "#4c8dff" }]} /></div>
        <table>
          <thead><tr><th>年份</th><th>回报</th></tr></thead>
          <tbody>{Object.entries(p.yearly ?? {}).map(([y, v]) => (
            <tr key={y}><td>{y}</td><td>{v.toFixed(2)}%</td></tr>))}
          </tbody>
        </table>
        <h2>历史压力测试</h2>
        <table><thead><tr><th>危机事件</th><th>时间</th><th>最大回撤</th></tr></thead><tbody>{p.stress_tests?.map((s) => <tr key={s.name}><td>{s.name}</td><td>{s.s} ~ {s.e}</td><td>{s.d}%</td></tr>)}</tbody></table>
        <p className="muted">风险提示：历史回测不代表未来表现；组合含海外资产，注意汇率与税费差异。</p>
      </section>
    </div>
  );
}
