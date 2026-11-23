import { Fragment } from "react";
import type { Dimension } from "../types";

export function ScoreGauge({ score }: { score: number | null }) {
  const s = score ?? 0;
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: 54, fontWeight: 800, color: "var(--accent)", lineHeight: 1 }}>
        {score ?? "--"}
      </div>
      <div className="bar" style={{ width: 190, margin: "10px auto 4px" }}>
        <div style={{ width: `${s}%` }} />
      </div>
      <div className="muted">综合评分 / 100</div>
    </div>
  );
}

export function DimensionCard({ d }: { d: Dimension }) {
  return (
    <div className="card">
      <h3 style={{ fontSize: 15 }}>
        {d.name} <span className="muted">权重 {d.weight}%{d.weight_effective != null && d.status === "ok" ? `（有效 ${d.weight_effective}%）` : ""}</span>
      </h3>
      {d.status === "ok" ? (
        <>
          <div>
            原始值 <b>{d.value ?? "--"}{d.unit}</b> · 评分 <span className="score">{d.score}</span>
          </div>
          <div className="bar" style={{ margin: "8px 0" }}>
            <div style={{ width: `${d.score ?? 0}%` }} />
          </div>
        </>
      ) : (
        <div className="muted">数据不可用 — {d.note}</div>
      )}
      <div className="muted">{d.note} · 来源：{d.source}</div>
    </div>
  );
}

export function Heatmap({ monthly }: { monthly: Record<string, (number | null)[]> }) {
  const years = Object.keys(monthly).sort();
  const color = (v: number | null) =>
    v == null ? "transparent" : v >= 0 ? `rgba(46,189,133,${Math.min(0.15 + v / 12, 0.9)})` : `rgba(229,72,77,${Math.min(0.15 - v / 12, 0.9)})`;
  return (
    <div className="heat">
      <div></div>
      {Array.from({ length: 12 }, (_, i) => <div key={i} className="muted">{i + 1}月</div>)}
      {years.map((y) => (
        <Fragment key={y}>
          <div className="muted" style={{ textAlign: "right", paddingRight: 6 }}>{y}</div>
          {monthly[y].map((v, i) => (
            <div key={`${y}-${i}`} style={{ background: color(v) }}>{v == null ? "" : v.toFixed(1)}</div>
          ))}
        </Fragment>
      ))}
    </div>
  );
}

export function SignalFeed({ lines }: { lines: string[] }) {
  return (
    <div className="term">
      {lines.map((l, i) => <div key={i}>&gt; {l}</div>)}
    </div>
  );
}

export function Drawer({ title, onClose, children }: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <>
      <div className="drawer-mask" onClick={onClose} />
      <div className="drawer">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ margin: 0 }}>{title}</h3>
          <button className="btn" onClick={onClose}>关闭</button>
        </div>
        {children}
      </div>
    </>
  );
}
