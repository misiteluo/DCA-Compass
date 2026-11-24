import { useEffect, useId, useRef } from "react";
import type { Dimension } from "../types";

export function ScoreGauge({ score }: { score: number | null }) {
  const s = score ?? 0;
  return (
    <div className="score-gauge">
      <div className="gauge-value score">
        {score ?? "--"}
      </div>
      <div className="bar">
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

export function Heatmap({ monthly, totals = false }: { monthly: Record<string, (number | null)[]>; totals?: boolean }) {
  const years = Object.entries(monthly).sort(([a], [b]) => a.localeCompare(b));
  const months = Array.from({ length: 12 }, (_, i) => i);
  const averages = months.map((month) => {
    const available = years.flatMap(([, row]) => row[month] ?? []);
    return available.length ? available.reduce((sum, value) => sum + value, 0) / available.length : null;
  });
  const color = (v: number | null) =>
    v == null ? "transparent" : v >= 0 ? `rgba(46,189,133,${Math.min(0.15 + v / 12, 0.9)})` : `rgba(229,72,77,${Math.min(0.15 - v / 12, 0.9)})`;
  const format = (v: number | null, digits = 1) => v == null ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(digits)}%`;
  return (
    <div className="table-scroll" tabIndex={0} role="region" aria-label="月度收益热力图">
      <table className="heat">
        <thead><tr><th scope="col">年份</th>{months.map((m) => <th scope="col" key={m}>{m + 1}月</th>)}{totals && <th scope="col">年度</th>}</tr></thead>
        <tbody>{years.map(([year, values]) => <tr key={year}>
          <th scope="row">{year}</th>
          {months.map((month) => {
            const value = values[month] ?? null;
            return <td key={month} style={{ background: color(value) }} title={`${year}年${month + 1}月 ${format(value, 2)}`}>{format(value)}</td>;
          })}
          {totals && <td>{format(values.reduce<number>((sum, value) => sum + (value ?? 0), 0))}</td>}
        </tr>)}</tbody>
        {totals && <tfoot><tr><th scope="row">月均</th>{averages.map((value, i) => <td key={i} style={{ background: color(value) }}>{format(value)}</td>)}<td>—</td></tr></tfoot>}
      </table>
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
