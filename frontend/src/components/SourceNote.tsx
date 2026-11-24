import type { DataSource } from "../types";

export function formatCapturedAt(value?: string | null) {
  if (!value) return "--";
  if (value.length === 10) return value;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--";
  return new Intl.DateTimeFormat("zh-CN", { timeZone: "Asia/Shanghai", dateStyle: "short", timeStyle: "medium" }).format(date);
}

export default function SourceNote({ source }: { source?: DataSource }) {
  if (!source) return null;
  const label = { live: "实时读取", cached: "缓存数据", snapshot: "离线快照", report: "固定历史报告", unavailable: "数据不可用" }[source.mode] ?? source.mode;
  return <p className="muted" role="status">
    <a href={source.url} target="_blank" rel="noreferrer">{label} · 参考数据来源</a>
    {source.captured_at && ` · 采集于 ${formatCapturedAt(source.captured_at)}（北京时间）`}
    {["cached", "snapshot"].includes(source.mode) && " · 当前未取得实时更新"}
  </p>;
}
