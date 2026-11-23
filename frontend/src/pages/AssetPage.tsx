import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { BarChart, EChart, LineChart, RadarChart } from "../components/Charts";
import SourceNote from "../components/SourceNote";
import { DimensionCard, Heatmap, ScoreGauge } from "../components/Widgets";
import type { AssetDetail } from "../types";

const fmt = (v: number | null | undefined) => v == null ? "--" : v.toLocaleString(undefined, { maximumFractionDigits: 2 });

export default function AssetPage({ assetId }: { assetId?: string }) {
  const { id: routeId = "btc" } = useParams();
  const id = assetId ?? routeId;
  const [asset, setAsset] = useState<AssetDetail | null>(null);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [log, setLog] = useState(false);
  const [range, setRange] = useState(0);
  useEffect(() => {
    let active = true;
    setAsset(null); setError(""); setPage(1); setRange(0);
    const refresh = () => api.asset(id).then((a) => { if (active) { setAsset(a); setError(""); } }).catch((e) => { if (active) setError(String(e)); });
    void refresh();
    const timer = window.setInterval(refresh, 60000);
    return () => { active = false; window.clearInterval(timer); };
  }, [id]);
  if (!asset) return <div className="wrap"><p role="status">{error ? `加载失败：${error}` : "正在读取行情、评分与历史数据…"}</p></div>;
  if (asset.status !== "ok") return <div className="wrap"><p>该资产数据暂不可用。</p><SourceNote source={asset.source} /></div>;
  const a = asset, report = a.report;
  const lastDate = a.history[a.history.length - 1]?.date ?? "";
  // Keep calendar dates as ISO strings, without UTC/local time conversion.
  const cutoff = range ? `${Number(lastDate.slice(0, 4)) - range}${lastDate.slice(4)}` : "";
  const history = a.history.filter((h) => h.date >= cutoff);
  const step = Math.max(1, Math.ceil(history.length / 1000));
  const points = history.filter((_, i) => i % step === 0 || i === history.length - 1);
  const pages = Math.max(1, Math.ceil(history.length / 10)), currentPage = Math.min(page, pages);
  const records = history.slice().reverse().slice((currentPage - 1) * 10, currentPage * 10);
  const annual = report.strategyReturns ?? report.returns ?? [];
  const years = report.years?.length === annual.length ? report.years : annual.map((_, i) => String(2015 + i));
  const monthly = report.monthlyData?.length && Array.isArray(report.monthlyData[0])
    ? Object.fromEntries((report.monthlyData as number[][]).map((row, i) => [String(2015 + i), row])) : null;
  const final = (values?: number[]) => values?.[values.length - 1] ?? null;
  return <div className="wrap">
    <section>
      <div className="card asset-head"><div>
        <h1>{a.name} 定投估值计算机</h1>
        <div className="price">{a.currency}{fmt(a.price)} <span className={(a.change_pct ?? 0) >= 0 ? "up" : "down"}>{fmt(a.change_pct)}%</span></div>
        <p>当前评分 <b>{a.score}</b> · {a.zone} · 今日定投 <b className="score">{fmt(a.multiplier)}x</b></p>
        <p>{a.action}</p>
        {a.yesterday_score != null && <p>昨日 {a.yesterday_score} 分 · 评分变化 {fmt(a.score_change)}</p>}
        {a.ma200 != null && <p className="muted">{id === "btc" ? "200 周均线" : "200 日均线"} {a.currency}{fmt(a.ma200)} · 偏离 {fmt(a.ma200_dev_pct)}%</p>}
        <p className="muted">数据日期 {a.date}</p>
      </div><ScoreGauge score={a.score} /></div>
      <SourceNote source={a.source} />
      {error && <p role="alert">刷新失败，保留上次结果：{error}</p>}
      {a.risk_control?.active && <p className="card">风控已触发：{a.risk_control.flags.join(" · ")}；当前倍数已包含原站风控结果。</p>}
      {a.data_quality?.staleFields?.length ? <p className="muted">部分指标为估算或未更新：{a.data_quality.staleFields.join("、")}</p> : null}
    </section>
    <section><h2>评分维度 · {a.dimensions.length} 维</h2>
      <div className="grid dimension-grid">{a.dimensions.map((d) => <DimensionCard key={d.key} d={d} />)}</div>
      <div className="card chart-card"><RadarChart names={a.dimensions.map((d) => d.name)} scores={a.dimensions.map((d) => d.score)} /></div>
    </section>
    {a.secondary && <section><h2>12 维度量化系统</h2>
      <p>独立评分 {a.secondary.score} · 倍数 {a.secondary.multiplier}x</p>
      <p className="muted">四维主评分和独立十二维评分分别展示。</p>
      <div className="grid dimension-grid">{a.secondary.dimensions.map((d) => <DimensionCard key={d.key} d={d} />)}</div>
      <div className="card"><RadarChart names={a.secondary.dimensions.map((d) => d.name)} scores={a.secondary.dimensions.map((d) => d.score)} /></div>
      <SourceNote source={a.secondary.source} />
    </section>}
    <section><h2>历史价格、评分与定投倍数</h2>
      <div className="toolbar">{[0, 1, 3, 5, 10].map((r) => <button key={r} className={`btn${range === r ? " on" : ""}`} onClick={() => { setRange(r); setPage(1); }}>{r ? `${r} 年` : "全部"}</button>)}</div>
      <div className="card"><EChart option={{
        tooltip: { trigger: "axis" }, legend: { textStyle: { color: "#c8d2de" } }, grid: { left: 75, right: 100, bottom: 60 },
        xAxis: { type: "category", data: points.map((p) => p.date) },
        yAxis: [{ type: "value", name: "价格", scale: true }, { type: "value", name: "评分", min: 0, max: 100 }, { type: "value", name: "倍数", position: "right", offset: 45, min: 0, max: 3 }],
        dataZoom: [{ type: "inside" }, { type: "slider", bottom: 0 }],
        series: [
          { name: "价格", type: "line", data: points.map((p) => p.price), showSymbol: false, yAxisIndex: 0 },
          { name: "评分", type: "line", data: points.map((p) => p.score), showSymbol: false, yAxisIndex: 1 },
          { name: "定投倍数", type: "line", data: points.map((p) => p.multiplier), showSymbol: false, yAxisIndex: 2 },
        ],
      }} /></div>
      <SourceNote source={a.history_source} />
      <div className="table-scroll"><table><thead><tr><th>日期</th><th>价格</th><th>评分</th><th>倍数</th><th>FGI / PE</th><th>状态</th></tr></thead>
        <tbody>{records.map((r) => <tr key={r.date}><td>{r.date}</td><td>{fmt(r.price)}</td><td>{fmt(r.score)}</td><td>{r.multiplier == null ? "--" : `${fmt(r.multiplier)}x`}</td><td>{fmt(r.fgi ?? r.pe)}</td><td>{r.event || "--"}</td></tr>)}</tbody></table></div>
      <div className="toolbar"><button className="btn" disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}>上一页</button><span>第 {currentPage} / {pages} 页 · {history.length} 条</span><button className="btn" disabled={currentPage === pages} onClick={() => setPage(currentPage + 1)}>下一页</button></div>
      {id === "hs300" && <div className="card"><h3>历史定投回测明细 · 月度基准 100</h3><div className="table-scroll"><table><thead><tr><th>日期</th><th>PE</th><th>评分</th><th>倍数</th><th>本次投入</th><th>累计投入</th><th>组合市值</th><th>收益率</th></tr></thead><tbody>{records.map((r) => <tr key={r.date}><td>{r.date}</td>{[r.pe, r.score, r.multiplier, r.amount, r.invested, r.value, r.return_pct].map((v, i) => <td key={i}>{fmt(v)}{i === 6 ? "%" : ""}</td>)}</tr>)}</tbody></table></div></div>}
    </section>
    <section><h2>历史回测报告</h2>
      <p className="muted">以下为参考站公布的固定历史报告，数值、区间与当前行情分别展示。</p>
      <div className="grid cards5">{report.metrics.map((m, i) => <div className="card" key={i}>{m}</div>)}</div>
      {!!annual.length && <div className="card chart-card"><h3>年度回报对比</h3><BarChart cats={years} series={[
        { name: "策略DCA", data: annual, color: "#f0b90b" },
        ...(report.dcaReturns || report.standardReturns ? [{ name: "普通DCA", data: report.dcaReturns ?? report.standardReturns ?? [], color: "#4c8dff" }] : []),
        ...(report.bhReturns || report.buyholdReturns ? [{ name: "买入持有", data: report.bhReturns ?? report.buyholdReturns ?? [], color: "#2ebd85" }] : []),
      ]} /></div>}
      {report.drawdowns && <div className="card chart-card"><h3>历史回撤</h3><LineChart dates={report.dates ?? []} series={[{ name: "回撤 %", data: report.drawdowns, color: "#e5484d" }]} /></div>}
      {monthly && <div className="card chart-card"><h3>月度收益热力图</h3><div className="table-scroll"><Heatmap monthly={monthly} /></div></div>}
      {report.tables.map((t, i) => <div key={i} className="card chart-card"><h3>{t.title}</h3><div className="table-scroll"><table><thead><tr>{t.rows[0].map((c, j) => <th key={j}>{c}</th>)}</tr></thead><tbody>{t.rows.slice(1).map((r, j) => <tr key={j}>{r.map((c, k) => <td key={k}>{c}</td>)}</tr>)}</tbody></table></div></div>)}
      {report.bins && <div className="card chart-card"><h3>收益分布</h3><BarChart cats={report.bins} series={[{ name: "频次", data: report.counts ?? [] }]} /></div>}
      {report.growthLabels && <div className="card chart-card"><h3>资金增长曲线</h3><button className="btn" onClick={() => setLog(!log)}>{log ? "切换线性" : "切换对数"}</button><LineChart log={log} dates={report.growthLabels} series={[
        { name: "策略DCA", data: report.strategyValue ?? [], color: "#f0b90b" }, { name: "普通DCA", data: report.standardValue ?? [], color: "#4c8dff" }, { name: "买入持有", data: report.bhValue ?? [], color: "#2ebd85" },
      ]} /></div>}
      {!!report.risk_return?.length && <div className="card chart-card"><h3>风险收益分布</h3><EChart option={{ tooltip: {}, legend: { textStyle: { color: "#c8d2de" } }, xAxis: { name: "最大回撤 %", type: "value", scale: true }, yAxis: { name: "总回报 %", type: "value" }, series: report.risk_return.map((p) => ({ name: p.name, type: "scatter", symbolSize: 18, data: [[p.drawdown, p.return_pct]] })) }} /></div>}
      {report.strategyValue && <div className="card chart-card"><h3>投入与产出对比</h3><BarChart cats={["策略DCA", "普通DCA", "买入持有"]} series={[
        ...(report.capital_invested ? [{ name: "总投入", data: report.capital_invested, color: "#8b98a9" }] : []),
        ...(report.capital_profit ? [{ name: "累计收益", data: report.capital_profit, color: "#2ebd85" }] : []),
        { name: "期末市值", data: [final(report.strategyValue), final(report.standardValue), final(report.bhValue)], color: "#f0b90b" },
      ]} /></div>}
      {report.narrative.map((text, i) => <p key={i} className="card report-text">{text}</p>)}
    </section>
    {a.trades && <section><h2>机器人定投记录</h2><SourceNote source={a.trades_source} />
      <div className="table-scroll"><table><thead><tr>{["日期", "点位", "评分", "倍数", "投入", "买入份额", "累计投入", "累计份额", "市值", "利润", "收益率"].map((s) => <th key={s}>{s}</th>)}</tr></thead><tbody>{a.trades.slice().reverse().map((t) => <tr key={t.trade_date}><td>{t.trade_date}</td>{[t.price, t.score, t.multiplier, t.amount, t.shares_bought, t.total_invested, t.total_shares, t.market_value, t.profit, t.return_rate].map((v, i) => <td key={i}>{fmt(v)}{i === 9 ? "%" : ""}</td>)}</tr>)}</tbody></table></div>
      {!a.trades.length && <p>暂无交易记录</p>}
    </section>}
    <section><h2>策略说明、倍数映射与风控</h2><div className="grid">{report.strategy.map((s, i) => <div className="card report-text" key={i}>{s}</div>)}</div></section>
  </div>;
}
