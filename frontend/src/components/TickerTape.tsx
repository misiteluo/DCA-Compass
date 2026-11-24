import { Link } from "react-router-dom";
import type { AssetSummary } from "../types";

export const fmtPrice = (a: AssetSummary) =>
  a.price == null ? "--" : `${a.currency}${a.price.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const fmtMultiplier = (a: AssetSummary) => a.multiplier == null ? "--" : `${a.multiplier.toFixed(2)}x`;

export default function TickerTape({ assets }: { assets: AssetSummary[] }) {
  return (
    <div className="tape">
      {assets.map((a) => (
        <Link key={a.id} to={`/${a.id}/`}>
          {a.name} <b>{fmtPrice(a)}</b>{" "}
          <span className={(a.change_pct ?? 0) >= 0 ? "up" : "down"}>
            {a.change_pct != null ? `${a.change_pct >= 0 ? "+" : ""}${a.change_pct}%` : "--"}
          </span>{" "}
          · 评分 <b>{a.score ?? "--"}</b> · 倍数 <b>{fmtMultiplier(a)}</b>
        </Link>
      ))}
    </div>
  );
}
