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
}

export interface Dimension {
  key: string;
  name: string;
  weight: number;
  weight_effective?: number;
  value: number | null;
  unit: string;
  score: number | null;
  status: string;
  source: string;
  note: string;
}

export interface StrategyResult {
  invested: number;
  final_value: number;
  total_return_pct: number;
  cagr_pct: number;
}

export interface Backtest {
  period: string;
  base_weekly: number;
  method_note: string;
  strategy: StrategyResult;
  regular: StrategyResult;
  buyhold: StrategyResult;
  risk: {
    max_drawdown_pct: number;
    sharpe: number;
    sortino: number;
    volatility_pct: number;
    note: string;
  };
  yearly: { year: number; strategy_pct: number; regular_pct: number; buyhold_pct: number | null }[];
  monthly: Record<string, (number | null)[]>;
  rolling: { years: number; annualized_pct: number }[];
  distribution: { bucket: string; weeks: number }[];
  growth_curve: { date: string; strategy: number; regular: number; buyhold: number }[];
  stress_tests: { label: string; period: string; asset_return_pct: number; max_drawdown_pct: number }[];
  best_year: { year: number; strategy_pct: number } | null;
  worst_year: { year: number; strategy_pct: number } | null;
}

export interface AssetDetail extends AssetSummary {
  prev_close: number | null;
  ma200: number | null;
  ma200_dev_pct: number | null;
  dimensions: Dimension[];
  mapping_table: { range: string; multiplier: number }[];
  price_history: { date: string; close: number }[];
  backtest: Backtest;
  config: { principal: string; period: string; monthly: string };
  risk_rules: string[];
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
  manager?: { name: string; tenure: string } | null;
  allocation?: Record<string, number> | null;
  fees?: number | null;
}

export interface Portfolio {
  id: string;
  name: string;
  risk: string;
  allocation: Record<string, number>;
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
}
