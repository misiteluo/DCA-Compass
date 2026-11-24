import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import TickerTape, { fmtMultiplier, fmtPrice } from "../components/TickerTape";
import { formatCapturedAt } from "../components/SourceNote";
import { SignalFeed } from "../components/Widgets";
import type { MarketOverview } from "../types";

const STEPS = [
  ["1 · 数据采集", "交易所行情、链上节点、宏观数据库与情绪指标"],
  ["2 · 指标计算", "每个资产按自己的维度体系计算原始指标值"],
  ["3 · 归一化", "根据各资产的历史分布与阈值，将原始值换算为 0–100 分"],
  ["4 · 加权计算", "综合分 = Σ（维度分 × 权重），权重合计 100%"],
  ["5 · 倍数映射", "按资产对应的分段线性、线性或指数规则换算定投倍数"],
  ["6 · 输出决策", "结合风控状态输出评分、倍数与操作建议"],
];

const MODELS = [
  ["btc", "比特币 · 7 维", "AHR999、MVRV、200 周均线、恐惧贪婪、矿工收益、持币风险、算力丝带"],
  ["gold", "黄金 · 7 维", "美元指数、实际利率、MA200、RSI、VIX、MACD、季节性"],
  ["nasdaq", "纳斯达克100 · 4 维与 12 维", "估值、技术、宏观和情绪主评分，另有 PE、PB、均线、波动率等十二维模型"],
  ["sp500", "标普500 · 10 维", "传统估值、CAPE、技术、宏观、情绪、行业、股息、波动、盈利与流动性"],
  ["hs300", "沪深300 · 10 维", "估值、趋势、波动、资金流、拥挤度等十项桥水风格指标"],
];

export default function Home() {
  const [market, setMarket] = useState<MarketOverview>();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    let timer: number;
    const refresh = async () => {
      try {
        const next = await api.markets(controller.signal);
        if (controller.signal.aborted) return;
        setMarket(next);
        setFailed(false);
      } catch {
        if (!controller.signal.aborted) setFailed(true);
      } finally {
        if (!controller.signal.aborted) timer = window.setTimeout(refresh, 30_000);
      }
    };
    void refresh();
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, []);

  const assets = market?.assets ?? [];
  const age = market?.data_at ? Math.max(0, Math.round((Date.now() - Date.parse(market.data_at)) / 1000)) : NaN;
  const upstreamCached = market?.source.mode === "live" && age >= 60;
  const status = failed ? (market ? "刷新失败，显示上次数据" : "行情加载失败，将自动重试")
    : upstreamCached || market?.source.mode === "cached" ? "缓存行情"
    : market?.source.mode === "live" ? (Number.isFinite(age) ? "实时行情" : "已连接行情来源")
    : market?.source.mode === "snapshot" ? "离线快照"
    : market ? "行情暂不可用" : "正在获取行情…";
  const feedLines = assets.map((a) => a.status === "unavailable" ? `${a.name} · 行情暂不可用`
    : `${a.name} · 现价 ${fmtPrice(a)} · 综合评分 ${a.score}（${a.zone ?? "--"}）· 定投倍数 ${fmtMultiplier(a)}`);

  return (
    <main>
      <TickerTape assets={assets} />
      <div className="wrap">
        <header>
          <h1>定投估值计算机实验室</h1>
          <p>查看五类资产的最新估值、定投倍数及历史回测。</p>
          <p className="muted"><span role="status">{status}</span>
            {!failed && upstreamCached && ` · ${age} 秒前`}
            {market?.data_at && ` · 行情时间 ${formatCapturedAt(market.data_at)}（北京时间）`}
            {market && <> · <a href={market.source.url} target="_blank" rel="noreferrer">数据来源</a></>}
          </p>
        </header>
        <section>
          <h2>资产行情</h2>
          <div className="grid cards5">
            {assets.map((a) => (
              <Link key={a.id} to={`/${a.id}/`} className="card">
                <h3>{a.name} <span className="muted">{a.name_en}</span></h3>
                <div className="price">{fmtPrice(a)}</div>
                <div className={(a.change_pct ?? 0) >= 0 ? "up" : "down"}>
                  {a.change_pct != null ? `${a.change_pct >= 0 ? "+" : ""}${a.change_pct}%` : "--"}
                </div>
                <div style={{ marginTop: 8 }}>
                  评分 <span className="score" style={{ fontSize: 20 }}>{a.score ?? "--"}</span>
                  {" "}· 倍数 <b>{fmtMultiplier(a)}</b>
                  {" "}· {a.zone ?? ""}
                </div>
                <p>{a.status === "unavailable" ? "行情暂不可用" : a.action ?? ""}</p>
                {a.date && <p className="muted">更新时间 {formatCapturedAt(a.date)}</p>}
              </Link>
            ))}
          </div>
        </section>

        {feedLines.length > 0 && <section>
          <h2>实时市场信号 · LIVE SIGNAL FEED</h2>
          <SignalFeed lines={feedLines} />
        </section>}

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

        {assets.length > 0 && <section>
          <h2 id="home-signals">定投信号</h2>
          <div className="table-scroll" tabIndex={0} role="region" aria-labelledby="home-signals"><table>
            <thead><tr>{["资产", "现价", "评分", "区间", "倍数", "建议动作"].map((label) => (
              <th scope="col" key={label}>{label}</th>
            ))}</tr></thead>
            <tbody>
              {assets.map((a) => (
                <tr key={a.id}>
                  <td><Link to={`/${a.id}/`}>{a.name}</Link></td>
                  <td>{fmtPrice(a)}</td><td>{a.score ?? "--"}</td><td>{a.zone ?? "--"}</td>
                  <td>{fmtMultiplier(a)}</td><td>{a.action ?? "--"}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </section>}

        <section>
          <h2>DCA 评分计算工作流</h2>
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))" }}>
            {STEPS.map(([t, d]) => (
              <div key={t} className="card"><h3 style={{ fontSize: 15 }}>{t}</h3><p className="muted">{d}</p></div>
            ))}
          </div>
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(210px,1fr))", marginTop: 14 }}>
            {MODELS.map(([id, title, description]) => (
              <Link key={id} to={`/${id}/`} className="card">
                <h3>{title}</h3>
                <p className="muted">{description}</p>
              </Link>
            ))}
          </div>
        </section>

        <p className="muted" style={{ marginTop: 34 }}>
          风险提示：本系统基于历史数据回测，不构成投资建议。回测收益不代表未来表现。
        </p>
      </div>
    </main>
  );
}
