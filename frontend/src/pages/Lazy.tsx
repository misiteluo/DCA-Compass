import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { PieChart } from "../components/Charts";
import type { Portfolio } from "../types";

export function LazyList() {
  const [list, setList] = useState<Portfolio[]>([]);
  useEffect(() => { api.portfolios().then(setList).catch(() => undefined); }, []);
  return (
    <div className="wrap">
      <section>
        <h2>全球十大懒人投资组合</h2>
        <p className="muted">全部组合由后端用真实 ETF 行情回测（2017 年至今，季度再平衡），不是引用第三方截图数字。</p>
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
  useEffect(() => { api.portfolio(id).then(setP).catch(() => undefined); }, [id]);
  if (!p) return <div className="wrap"><p>加载中…</p></div>;
  return (
    <div className="wrap">
      <p><Link to="/lazy">← 返回所有组合</Link></p>
      <section style={{ marginTop: 8 }}>
        <h2>{p.name}</h2>
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
            <div className="kv"><span>再平衡规则</span><b>{p.rebalance}</b></div>
            <div className="kv"><span>适用人群</span><b>{p.suitable}</b></div>
            <p className="muted">{p.note}</p>
          </div>
        </div>
      </section>
      <section>
        <h2>年度回报</h2>
        <table>
          <thead><tr><th>年份</th><th>回报</th></tr></thead>
          <tbody>{Object.entries(p.yearly ?? {}).map(([y, v]) => (
            <tr key={y}><td>{y}</td><td>{v}%</td></tr>))}
          </tbody>
        </table>
        <p className="muted">风险提示：历史回测不代表未来表现；组合含海外资产，注意汇率与税费差异。</p>
      </section>
    </div>
  );
}
