import type { AssetDetail, AssetSummary, Fund, FundMarketScore, Portfolio } from "../types";

const BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json() as Promise<T>;
}

export const api = {
  assets: () => get<AssetSummary[]>("/assets"),
  asset: (id: string) => get<AssetDetail>(`/assets/${id}`),
  weeklySignals: () =>
    get<{ signals: AssetSummary[] & Record<string, unknown>[] }>("/signals/weekly"),
  funds: (kind: "active" | "passive") => get<Fund[]>(`/funds?kind=${kind}`),
  fund: (code: string) => get<Fund>(`/funds/${code}`),
  fundMarketScore: () => get<FundMarketScore>("/fund-market-score"),
  portfolios: () => get<Portfolio[]>("/portfolios"),
  portfolio: (id: string) => get<Portfolio>(`/portfolios/${id}`),
};
