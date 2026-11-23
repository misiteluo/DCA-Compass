import { Link } from "react-router-dom";
import type { AssetSummary } from "../types";

export const fmtPrice = (a: AssetSummary) =>
  a.price == null ? "--" : `${a.currency}${a.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;

export default function TickerTape({ assets }: { assets: AssetSummary[] }) {
  return (
    <div className="tape">
      {assets.map((a) => (
        <Link key={a.id} to={`/asset/${a.id}`}>
          {a.name} <b>{fmtPrice(a)}</b>{" "}
          <span className={(a.change_pct ?? 0) >= 0 ? "up" : "down"}>
            {a.change_pct != null ? `${a.change_pct >= 0 ? "+" : ""}${a.change_pct}%` : "--"}
          </span>{" "}
          · 评分 <b>{a.score ?? "--"}</b> · 倍数 <b>{a.multiplier != null ? `${a.multiplier}x` : "--"}</b>
        </Link>
      ))}
    </div>
  );
}
