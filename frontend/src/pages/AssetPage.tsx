import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { BarChart, LineChart, RadarChart } from "../components/Charts";
import { DimensionCard, Heatmap, ScoreGauge } from "../components/Widgets";
import type { AssetDetail } from "../types";

const fmt = (v: number | null | undefined, digits = 2) =>
  v == null ? "--" : v.toLocaleString(undefined, { maximumFractionDigits: digits });

export default function AssetPage() {
  const { id = "btc" } = useParams();
  const [a, setA] = useState<AssetDetail | null>(null);
  const [log, setLog] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    setA(null);
    api.asset(id).then(setA).catch((e) => setErr(String(e)));
  }, [id]);

  if (err) return <div className="wrap"><p>加载失败：{err}</p></div>;
  if (!a) return <div className="wrap"><p>加载中…（首次加载需抓取并计算历史数据）</p></div>;
  const bt = a.backtest;
  const inOut = [
    { name: "策略DCA", inv: bt.strategy.invested, fin: bt.strategy.final_value },
    { name: "普通DCA", inv: bt.regular.invested, fin: bt.regular.final_value },
    { name: "买入持有", inv: bt.buyhold.invested, fin: bt.buyhold.final_value },
  ];

  return (
    <div className="wrap">
      <section style={{ marginTop: 22 }}>
        <div className="card" style={{ display: "flex", gap: 28, flexWrap: "wrap", alignItems: "center" }}>
          <div>
            <h1 style={{ margin: "0 0 4px", fontSize: 26 }}>{a.name} 定投估值计算机</h1>
            <div className="price" style={{ fontSize: 30, fontWeight: 800 }}>
              {a.currency}{fmt(a.price)}
              <span className={(a.change_pct ?? 0) >= 0 ? "up" : "down"} style={{ fontSize: 17, marginLeft: 10 }}>
                {a.change_pct != null ? `${a.change_pct >= 0 ? "+" : ""}${a.change_pct}%` : ""}
              </span>
            </div>
            <div className="muted">
              数据日期 {a.date} · MA200 {a.currency}{fmt(a.ma200)} · 偏离度 {fmt(a.ma200_dev_pct)}%
            </div>
            <div style={{ marginTop: 8, fontSize: 17 }}>
              区间 <b>{a.zone}</b> · 建议 <b>{a.action}</b> · 本周倍数{" "}
              <span className="score" style={{ fontSize: 22 }}>{a.multiplier ?? "--"}x</span>
            </div>
          </div>
          <div style={{ marginLeft: "auto" }}><ScoreGauge score={a.score} /></div>
        </div>
      </section>

      <section>
        <h2>评分维度</h2>
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(250px,1fr))" }}>
          {a.dimensions.map((d) => <DimensionCard key={d.key} d={d} />)}
        </div>
      </section>

      <section>
        <h2>维度雷达图</h2>
        <div className="card">
          <RadarChart names={a.dimensions.map((d) => d.name)} scores={a.dimensions.map((d) => d.score)} />
          <p className="muted">数据不可用的维度在雷达图上记为 0，综合分已按剩余维度权重重新归一化。</p>
        </div>
      </section>

      <section>
        <h2>价格走势（周频）</h2>
        <div className="card">
          <LineChart dates={a.price_history.map((p) => p.date)}
            series={[{ name: a.name, data: a.price_history.map((p) => p.close), color: "#f0b90b" }]} />
        </div>
      </section>

      <section>
        <h2>年度回报对比</h2>
        <div className="card">
          <BarChart cats={bt.yearly.map((y) => String(y.year))} series={[
            { name: "策略DCA", data: bt.yearly.map((y) => y.strategy_pct), color: "#f0b90b" },
            { name: "普通DCA", data: bt.yearly.map((y) => y.regular_pct), color: "#4c8dff" },
            { name: "买入持有(资产)", data: bt.yearly.map((y) => y.buyhold_pct), color: "#2ebd85" },
          ]} />
          <p className="muted">
            最佳年份 {bt.best_year?.year}（策略 {bt.best_year?.strategy_pct}%）·
            最差年份 {bt.worst_year?.year}（策略 {bt.worst_year?.strategy_pct}%）
          </p>
        </div>
      </section>

      <section>
        <h2>滚动收益（资产，年化）</h2>
        <table><thead><tr><th>周期</th><th>年化收益</th></tr></thead>
          <tbody>{bt.rolling.map((r) => <tr key={r.years}><td>{r.years} 年</td><td>{r.annualized_pct}%</td></tr>)}</tbody>
        </table>
      </section>

      <section>
        <h2>月度收益热力图（资产，%）</h2>
        <div className="card"><Heatmap monthly={bt.monthly} /></div>
      </section>

      <section>
        <h2>风险与回报指标</h2>
        <table>
          <thead><tr><th>策略</th><th>总投入</th><th>期末市值</th><th>总回报</th><th>CAGR</th></tr></thead>
          <tbody>
            {inOut.map((s) => (
              <tr key={s.name}><td>{s.name}</td><td>{fmt(s.inv, 0)}</td><td>{fmt(s.fin, 0)}</td>
                <td>{s.name === "策略DCA" ? bt.strategy.total_return_pct : s.name === "普通DCA" ? bt.regular.total_return_pct : bt.buyhold.total_return_pct}%</td>
                <td>{s.name === "策略DCA" ? bt.strategy.cagr_pct : s.name === "普通DCA" ? bt.regular.cagr_pct : bt.buyhold.cagr_pct}%</td></tr>
            ))}
          </tbody>
        </table>
        <p className="muted">
          策略组合最大回撤 {bt.risk.max_drawdown_pct}% · 夏普 {bt.risk.sharpe} · 索提诺 {bt.risk.sortino} ·
          年化波动 {bt.risk.volatility_pct}%（{bt.risk.note}）
        </p>
      </section>

      <section>
        <h2>压力测试（窗口内资产表现）</h2>
        <table>
          <thead><tr><th>事件</th><th>区间</th><th>资产收益</th><th>最大回撤</th></tr></thead>
          <tbody>{bt.stress_tests.map((s) => (
            <tr key={s.label}><td>{s.label}</td><td>{s.period}</td><td>{s.asset_return_pct}%</td><td>{s.max_drawdown_pct}%</td></tr>
          ))}</tbody>
        </table>
      </section>

      <section>
        <h2>收益分布（周收益率）</h2>
        <div className="card">
          <BarChart cats={bt.distribution.map((d) => d.bucket)}
            series={[{ name: "周数", data: bt.distribution.map((d) => d.weeks), color: "#4c8dff" }]} />
        </div>
      </section>

      <section>
        <h2>资金增长曲线</h2>
        <div className="card">
          <button className="btn" onClick={() => setLog(!log)}>{log ? "切换线性" : "切换对数"}</button>
          <LineChart log={log} dates={bt.growth_curve.map((c) => c.date)} series={[
            { name: "策略DCA", data: bt.growth_curve.map((c) => c.strategy), color: "#f0b90b" },
            { name: "普通DCA", data: bt.growth_curve.map((c) => c.regular), color: "#4c8dff" },
            { name: "买入持有", data: bt.growth_curve.map((c) => c.buyhold), color: "#2ebd85" },
          ]} />
        </div>
      </section>

      <section>
        <h2>投入产出对比</h2>
        <div className="card">
          <BarChart cats={inOut.map((s) => s.name)} series={[
            { name: "总投入", data: inOut.map((s) => s.inv), color: "#8b98a9" },
            { name: "期末市值", data: inOut.map((s) => s.fin), color: "#f0b90b" },
          ]} />
        </div>
      </section>

      <section>
        <h2>回测数据报告</h2>
        <div className="card">
          <div className="kv"><span>回测区间</span><b>{bt.period}</b></div>
          <div className="kv"><span>定投方式</span><b>每周定投，基准 {bt.base_weekly}/周</b></div>
          <div className="kv"><span>策略总回报</span><b>{bt.strategy.total_return_pct}%（普通 {bt.regular.total_return_pct}% / 买入持有 {bt.buyhold.total_return_pct}%）</b></div>
          <p className="muted">{bt.method_note}。买入持有在长牛资产上常常跑赢定投，页面如实并列，不做挑选。</p>
        </div>
      </section>

      <section>
        <h2>倍数映射表</h2>
        <table>
          <thead><tr><th>评分区间</th><th>定投倍数</th></tr></thead>
          <tbody>{a.mapping_table.map((m) => (
            <tr key={m.range} style={m.multiplier === a.multiplier ? { background: "var(--panel2)" } : undefined}>
              <td>{m.range}</td><td>{m.multiplier}x</td></tr>
          ))}</tbody>
        </table>
      </section>

      <section>
        <h2>资金配置示例与风控规则</h2>
        <div className="card">
          <div className="kv"><span>本金</span><b>{a.config.principal}</b></div>
          <div className="kv"><span>周期</span><b>{a.config.period}</b></div>
          <div className="kv"><span>基准月投</span><b>{a.config.monthly}</b></div>
          <ul>{a.risk_rules.map((r) => <li key={r}>{r}</li>)}</ul>
        </div>
      </section>

      <p className="muted">本系统基于历史数据回测，不构成投资建议。</p>
    </div>
  );
}
