export interface AssetSummary {
  id: string;
  name: string;
  name_en: string;
  symbol: string;
  currency: string;
  status: string;
  price: number | null;
  change_pct: number | null;
  date: string | null;
  score: number | null;
  multiplier: number | null;
  zone: string | null;
  action: string | null;
  source?: DataSource;
}

export interface DataSource {
  mode: string;
  url: string;
  captured_at?: string;
  error?: string | null;
}

export interface MarketOverview {
  assets: AssetSummary[];
  source: DataSource;
  data_at: string | null;
}

export interface Dimension {
  key: string;
  name: string;
  weight: number;
  weight_effective?: number;
  value: number | string | null;
  unit: string;
  score: number | null;
  status: string;
  source: string;
  note: string;
  details?: Record<string, unknown>;
}

export interface AssetDetail extends AssetSummary {
  ma200: number | null;
  ma200_dev_pct: number | null;
  dimensions: Dimension[];
  yesterday_score?: number | null;
  score_change?: number | null;
  risk_control?: { active: boolean; flags: string[] };
  data_quality?: { fresh?: boolean; staleFields?: string[] };
  valuation?: { pe: number | null; pb: number | null };
  summary_indicators?: Dimension[];
  history: HistoryRow[];
  history_source: DataSource;
  secondary?: { score: number; multiplier: number; dimensions: Dimension[]; source: DataSource } | null;
  trades?: Trade[];
  trades_source?: DataSource;
  report: AssetReport;
}

export interface HistoryRow {
  date: string;
  price: number | null;
  score: number | null;
  multiplier: number | null;
  pe?: number | null;
  pb?: number | null;
  rsi?: number | null;
  dxy?: number | null;
  vix?: number | null;
  tips?: number | null;
  fgi?: number | null;
  event?: string;
  amount?: number;
  invested?: number;
  value?: number;
  return_pct?: number;
}

export interface Trade {
  trade_date: string;
  price: number;
  score: number;
  multiplier: number;
  amount: number;
  shares_bought: number;
  total_invested: number;
  total_shares: number;
  market_value: number;
  profit: number;
  return_rate: number;
}

export interface AssetReport {
  tables: { title: string; rows: string[][] }[];
  metrics: string[];
  strategy: string[];
  narrative: string[];
  years?: string[];
  comparison_years?: string[];
  yearly_highlights?: string[];
  returns?: number[];
  strategyReturns?: number[];
  dcaReturns?: number[];
  standardReturns?: number[];
  bhReturns?: number[];
  buyholdReturns?: number[];
  growthLabels?: string[];
  strategyValue?: number[];
  standardValue?: number[];
  bhValue?: number[];
  dates?: string[];
  drawdowns?: number[];
  monthlyData?: number[][] | { date: string; price: number; pe: number; pb: number; event: string }[];
  monthly_heatmap?: Record<string, (number | null)[]>;
  bins?: string[];
  counts?: number[];
  capital_invested?: number[];
  capital_profit?: number[];
  total_returns?: number[];
  risk_return?: { name: string; drawdown: number; return_pct: number }[];
}

export interface Fund {
  code: string;
  name: string;
  kind: string;
  status: string;
  scale_yi: number | null;
  inception: string | null;
  total_return_pct: number | null;
  annualized_pct: number | null;
  daily_change_pct: number | null;
  max_drawdown_pct: number | null;
  purchase_limit: number | null;
  returns?: Record<string, number | null>;
  risk?: { sharpe: number | null; volatility_pct: number | null; beta: number | null; alpha: number | null; note?: string };
  manager?: { name: string; tenure: string; desc?: string } | null;
  allocation?: Record<string, number> | null;
  fees?: Record<string, number> | null;
  benchmark_cagr_pct?: number | null;
  excess_return_pct?: number | null;
  beat_benchmark?: boolean;
  holdings_top10?: Holdings | null;
  holdings_full?: Holdings | null;
  source?: DataSource;
}

export interface Holdings {
  reportDate?: string;
  quarter?: string;
  holdings: { name: string; code?: string; weight: number; dailyChange?: number }[];
}

export interface FundMarketScore {
  score: number;
  multiplier: number;
  status: string;
  strategy: string;
  dimensions: Record<string, { score: number; weight: number; label: string }>;
  computedAt?: string;
  source: DataSource;
}

export interface Portfolio {
  id: string;
  name: string;
  risk: string;
  risk_level: number;
  ticker: string;
  allocation: Record<string, number>;
  allocation_labels: Record<string, string>;
  status: string;
  annualized_pct: number | null;
  volatility_pct: number | null;
  max_drawdown_pct: number | null;
  sharpe: number | null;
  period?: string;
  rebalance?: string;
  suitable?: string;
  note?: string;
  initial?: number;
  final_value?: number;
  yearly?: Record<string, number>;
  source?: DataSource;
  name_en?: string;
  founder?: string;
  philosophy?: string;
  sortino?: number;
  beta?: number;
  alpha?: number;
  r2?: number;
  best?: number;
  worst?: number;
  growth_curve?: { date: string; value: number }[];
  stress_tests?: { s: string; e: string; d: number; name: string }[];
}
