import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import TickerTape, { fmtPrice } from "../components/TickerTape";
import SourceNote, { formatCapturedAt } from "../components/SourceNote";
import { SignalFeed } from "../components/Widgets";
import type { AssetDetail, AssetSummary } from "../types";

const STEPS = [
  ["1 · 数据采集", "交易所行情、链上节点、宏观数据库与情绪指标"],
  ["2 · 指标计算", "每个资产按自己的维度体系计算原始指标值"],
  ["3 · 归一化", "按各资产的规则将原始值换算为 0–100 分"],
  ["4 · 加权计算", "综合分 = Σ（维度分 × 权重），权重合计 100%"],
  ["5 · 倍数映射", "综合分按各资产的映射表换算成 0–3x 定投倍数"],
  ["6 · 输出决策", "结合风控状态输出评分、倍数与操作建议"],
];

export default function Home() {
  const [assets, setAssets] = useState<AssetSummary[]>([]);
  const [details, setDetails] = useState<AssetDetail[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    let active = true;
    const refresh = () => api.assets().then((list) => {
      if (!active) return;
      setAssets(list); setErr("");
      return Promise.all(list.map((a) => api.asset(a.id))).then((d) => { if (active) setDetails(d); });
    }).catch((e) => { if (active) setErr(String(e)); });
    void refresh();
    const timer = window.setInterval(refresh, 60000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  if (err) return <div className="wrap"><p>后端数据加载失败：{err}（请确认 API 已启动）</p></div>;

  const feedLines = assets.flatMap((a) => [
    `[${a.date ?? ""}] ${a.name} 现价 ${fmtPrice(a)}，综合评分 ${a.score ?? "--"}（${a.zone ?? ""}），本周定投倍数 ${a.multiplier ?? "--"}x`,
  ]);

  return (
    <div>
      <TickerTape assets={assets} />
      <div className="wrap">
        <section>
          <div className="grid cards5">
            {assets.map((a) => (
              <Link key={a.id} to={`/asset/${a.id}`} className="card">
                <h3>{a.name} <span className="muted">{a.name_en}</span></h3>
                <div className="price">{fmtPrice(a)}</div>
                <div className={(a.change_pct ?? 0) >= 0 ? "up" : "down"}>
                  {a.change_pct != null ? `${a.change_pct >= 0 ? "+" : ""}${a.change_pct}%` : "--"}
                </div>
                <div style={{ marginTop: 8 }}>
                  评分 <span className="score" style={{ fontSize: 20 }}>{a.score ?? "--"}</span>
                  {" "}· 倍数 <b>{a.multiplier != null ? `${a.multiplier}x` : "--"}</b>
                  {" "}· {a.zone ?? ""}
                </div>
                <div className="term" style={{ marginTop: 10 }}>
                  <div>&gt; score = {a.score ?? "--"} → multiplier = {a.multiplier ?? "--"}x</div>
                  <div>&gt; zone: {a.zone ?? "--"} / action: {a.action ?? "--"}</div>
                  <div>&gt; updated: {a.date ?? "--"}</div>
                </div>
                <p className="muted">{a.source?.mode === "live" ? "实时读取" : "缓存 / 快照"} · {formatCapturedAt(a.source?.captured_at)}（北京时间）</p>
              </Link>
            ))}
          </div>
        </section>

        <section>
          <h2>实时市场信号 · LIVE SIGNAL FEED</h2>
          <SignalFeed lines={feedLines.length ? feedLines : ["正在加载信号…"]} />
        </section>

        <section>
          <h2>DCA 实验室 · 智能定投策略</h2>
          <div className="card">
            <p>
              普通定投的问题是：贵的时候和便宜的时候买一样多。本站的做法是给每个资产每天算一个
              0–100 的估值分，再把分数换算成定投倍数——便宜时多买，贵时少买甚至暂停。
              五个资产用同一套流水线（采集 → 计算 → 归一化 → 加权 → 映射），但维度、权重和
              倍数映射按各自的市场结构分别设定。
            </p>
          </div>
        </section>

        <section>
          <h2>本周定投信号 · THIS WEEK'S DCA SIGNALS</h2>
          <div className="table-scroll"><table>
            <thead><tr><th>资产</th><th>现价</th><th>评分</th><th>区间</th><th>倍数</th><th>建议动作</th></tr></thead>
            <tbody>
              {assets.map((a) => (
                <tr key={a.id}>
                  <td><Link to={`/asset/${a.id}`}>{a.name}</Link></td>
                  <td>{fmtPrice(a)}</td><td>{a.score ?? "--"}</td><td>{a.zone ?? "--"}</td>
                  <td>{a.multiplier != null ? `${a.multiplier}x` : "--"}</td><td>{a.action ?? "--"}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </section>

        <section>
          <h2>DCA 评分计算工作流</h2>
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))" }}>
            {STEPS.map(([t, d]) => (
              <div key={t} className="card"><h3 style={{ fontSize: 15 }}>{t}</h3><p className="muted">{d}</p></div>
            ))}
          </div>
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(210px,1fr))", marginTop: 14 }}>
            {details.map((a) => (
              <div key={a.id} className="card">
                <h3 style={{ fontSize: 15 }}>{a.name} · {(a.secondary?.dimensions ?? a.dimensions).length} 个维度</h3>
                <p className="muted">{(a.secondary?.dimensions ?? a.dimensions).map((d) => `${d.name} ${d.weight}%`).join(" + ")}</p>
              </div>
            ))}
          </div>
        </section>
        <SourceNote source={assets[0]?.source} />

        <p className="muted" style={{ marginTop: 34 }}>
          风险提示：本系统基于历史数据回测，不构成投资建议。回测收益不代表未来表现。
        </p>
      </div>
    </div>
  );
}
