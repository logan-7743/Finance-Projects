export type ChartRange = "1D" | "5D" | "1M" | "6M" | "1Y" | "5Y";
export type ChartType = "candles" | "line";
export type IndicatorKind =
  | "ema"
  | "sma"
  | "atr"
  | "adx"
  | "rsi"
  | "macd"
  | "bollinger"
  | "vwap"
  | "stochastic"
  | "obv";
export type IndicatorPane = "overlay" | "oscillator";
export type IndicatorLineStyle = "line" | "histogram";
export type RuleOperator = "gt" | "lt" | "crosses_above" | "crosses_below";
export type RuleRightType = "indicator" | "value";

export interface OHLCVBar {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface HistoryResponse {
  symbol: string;
  period: string;
  interval: string;
  bars: OHLCVBar[];
  indicators: IndicatorSeries[];
}

export interface HistoryRequestOptions {
  since?: string;
  indicators?: IndicatorRequestConfig[];
}

export interface IndicatorRequestConfig {
  id: string;
  kind: IndicatorKind;
  params: Record<string, number>;
}

export interface IndicatorPoint {
  time: string;
  value: number;
}

export interface IndicatorLine {
  key: string;
  label: string;
  color: string;
  style: IndicatorLineStyle;
  points: IndicatorPoint[];
}

export interface IndicatorSeries {
  id: string;
  kind: IndicatorKind;
  name: string;
  pane: IndicatorPane;
  lines: IndicatorLine[];
}

export interface BacktestRule {
  left_indicator_id: string;
  left_line_key: string;
  operator: RuleOperator;
  right_type: RuleRightType;
  right_indicator_id?: string | null;
  right_line_key?: string | null;
  right_value?: number | null;
}

export interface BacktestConfig {
  initial_capital: number;
  entry_rules: BacktestRule[];
  exit_rules: BacktestRule[];
}

export interface BacktestTrade {
  entry_time: string;
  exit_time: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  gross_pnl: number;
  net_pnl: number;
  net_return_pct: number;
}

export interface BacktestMetrics {
  trade_count: number;
  total_return_pct: number;
  annualized_return_pct: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  calmar_ratio: number;
  win_rate_pct: number;
  avg_trade_return_pct: number;
  exposure_pct: number;
  profit_factor: number;
  ending_equity: number;
}

export interface BacktestResult {
  indicators: IndicatorSeries[];
  trades: BacktestTrade[];
  metrics: BacktestMetrics;
  equity_curve: [string, number][];
}

export interface StrategyBacktestResult {
  strategy_name: string;
  symbol: string;
  trades: BacktestTrade[];
  metrics: BacktestMetrics;
  equity_curve: [string, number][];
  signal_count: number;
}

export interface ResearchMetric {
  name: string;
  value: number | string;
  description?: string | null;
}

export interface BacktestReviewArtifact {
  strategy_name: string;
  symbol: string;
  hypothesis: string;
  data_range: string;
  cost_assumptions: string[];
  validation_notes: string[];
  metrics: ResearchMetric[];
  risks: string[];
}

export interface LlmReviewResult {
  provider: string;
  model: string;
  verdict: "reject" | "research_more" | "paper_trade_candidate" | "disable";
  report_markdown: string;
}

export interface PerplexityResearchResult {
  provider: string;
  model: string;
  answer_markdown: string;
  citations: Array<{
    title: string;
    url: string;
    date?: string | null;
  }>;
}

export interface BacktestRequest {
  symbol: string;
  range: ChartRange;
  period?: string | null;
  interval?: string | null;
  indicators: IndicatorRequestConfig[];
  config: BacktestConfig;
}

export interface QuoteResponse {
  symbol: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  market_cap: number | null;
  name: string | null;
}

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: init?.method ?? "GET",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    body: init?.body,
  });

  const bodyText = await response.text();

  if (!response.ok) {
    let message =
      bodyText || `Request failed with status ${response.status}`;
    try {
      const parsed = JSON.parse(bodyText) as { detail?: string };
      if (typeof parsed.detail === "string") {
        message = parsed.detail;
      }
    } catch {
      // Keep raw body text when the API did not return JSON.
    }
    throw new Error(message);
  }

  return JSON.parse(bodyText) as T;
}

export function getHistory(
  symbol: string,
  range: ChartRange,
  options: HistoryRequestOptions = {},
) {
  const params = new URLSearchParams({ symbol, range });
  if (options.since) {
    params.set("since", options.since);
  }
  if (options.indicators && options.indicators.length > 0) {
    params.set("indicators", JSON.stringify(options.indicators));
  }
  return request<HistoryResponse>(`/api/market/history?${params.toString()}`);
}

export function getQuote(symbol: string) {
  const params = new URLSearchParams({ symbol });
  return request<QuoteResponse>(`/api/market/quote?${params.toString()}`);
}

export function runIndicatorBacktest(payload: BacktestRequest) {
  return request<BacktestResult>("/api/market/backtest", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function runEmaCrossoverBacktest(payload: {
  symbol: string;
  period?: string;
  interval?: string;
  initial_capital: number;
  fast_period?: number;
  slow_period?: number;
  execution_lag_bars?: number;
}) {
  return request<StrategyBacktestResult>("/api/backtests/ema-crossover", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function reviewBacktestArtifact(payload: BacktestReviewArtifact) {
  return request<LlmReviewResult>("/api/research/review", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function runPerplexityResearch(payload: {
  question: string;
  system_prompt?: string;
  search_mode?: string;
  max_tokens?: number;
  temperature?: number;
}) {
  return request<PerplexityResearchResult>("/api/research/perplexity", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
