import { Fragment, useEffect, useId, useRef } from "react";
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
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    dialog.showModal();
    let pressedOutside = false;
    const outside = (e: PointerEvent) => {
      const r = dialog.getBoundingClientRect();
      return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
    };
    const down = (e: PointerEvent) => { pressedOutside = outside(e); };
    const up = (e: PointerEvent) => { if (pressedOutside && outside(e)) dialog.close(); };
    if (!("closedBy" in HTMLDialogElement.prototype)) {
      dialog.addEventListener("pointerdown", down);
      dialog.addEventListener("pointerup", up);
    }
    return () => { dialog.removeEventListener("pointerdown", down); dialog.removeEventListener("pointerup", up); dialog.close(); };
  }, []);
  return (
      <dialog ref={ref} className="drawer" aria-labelledby={titleId} {...{ closedby: "any" }} onClose={() => { if (ref.current?.open) return; if (ref.current) ref.current.returnValue = ""; onClose(); }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 id={titleId} style={{ margin: 0 }}>{title}</h3>
          <form method="dialog"><button className="btn" autoFocus>关闭</button></form>
        </div>
        {children}
      </dialog>
  );
}
