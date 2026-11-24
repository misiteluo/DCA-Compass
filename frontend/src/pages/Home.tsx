import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { formatCapturedAt } from "../components/SourceNote";
import type { AssetSummary, MarketOverview } from "../types";

const MARKET_COLUMNS = ["资产", "估值评分", "定投倍数", "现价", "涨跌幅", "信号"];

function formatPrice(asset: AssetSummary) {
  return asset.price == null ? "—" : `${asset.currency}${asset.price.toLocaleString("zh-CN", {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  })}`;
}

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
  return (
    <main className="wrap home">
      <header className="home-intro">
        <div>
          <h1>五资产定投信号</h1>
          <p>在一处比较比特币、黄金、纳指、标普 500 和沪深 300 的估值与定投倍数。</p>
          <Link className="btn primary" to="/touzi">查看策略手册</Link>
        </div>
        <dl className="signal-key">
          <div>
            <dt>估值评分</dt>
            <dd>0–100 分，分数越高，模型判断的估值越低。</dd>
          </div>
          <div>
            <dt>定投倍数</dt>
            <dd>以 1.00× 为基准，按倍数调整每期定投金额。</dd>
          </div>
        </dl>
      </header>

      <section className="market-panel" aria-labelledby="market-heading">
        <div className="market-header">
          <h2 id="market-heading">资产行情</h2>
          <div className="market-source muted">
            <span className="market-status" role="status">{status}{!failed && upstreamCached && ` · ${age} 秒前`}</span>
            {market?.data_at && <time dateTime={market.data_at}>{formatCapturedAt(market.data_at)}（北京时间）</time>}
            {market?.source.url && <a href={market.source.url} target="_blank" rel="noreferrer">数据来源</a>}
          </div>
        </div>
        {assets.length > 0 && (
          <>
            <p className="market-hint muted" id="market-hint">横向滑动查看现价、涨跌幅与信号</p>
            <div className="table-scroll market-scroll" tabIndex={0} role="region" aria-labelledby="market-heading" aria-describedby="market-hint">
              <table className="market-table">
                <thead>
                  <tr>{MARKET_COLUMNS.map((label) => <th scope="col" key={label}>{label}</th>)}</tr>
                </thead>
                <tbody>
                  {assets.map((asset) => {
                    const change = asset.change_pct;
                    return (
                      <tr key={asset.id}>
                        <th scope="row">
                          <Link className="market-asset" to={`/${asset.id}/`}>
                            <span className="asset-mark" aria-hidden="true">{{ btc: "₿", gold: "Au", nasdaq: "N", sp500: "S", hs300: "沪" }[asset.id]}</span>
                            <span>{asset.name}<small className="muted">{asset.name_en}</small></span>
                          </Link>
                        </th>
                        <td className="score">{asset.score ?? "—"}</td>
                        <td className="market-multiplier">{asset.multiplier == null ? "—" : `${asset.multiplier.toFixed(2)}×`}</td>
                        <td>{formatPrice(asset)}</td>
                        <td className={change == null || change === 0 ? "muted" : change > 0 ? "up" : "down"}>
                          {change == null ? "—" : `${change > 0 ? "+" : ""}${change}%`}
                        </td>
                        <td className="market-signal">
                          {asset.status === "unavailable" ? "行情暂不可用" : asset.action ?? "—"}
                          {asset.zone && asset.zone !== asset.action && <small className="muted">{asset.zone}</small>}
                          {asset.date && asset.date !== market?.data_at && <small className="muted">更新于 {formatCapturedAt(asset.date)}</small>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      <section className="home-method">
        <h2>评分如何计算</h2>
        <p>模型按资产采集市场数据，将各项指标换算为 0–100 分，再按权重合成估值评分。各资产根据自身规则将评分映射为定投倍数，并在触发风控时调整。</p>
      </section>
    </main>
  );
}
