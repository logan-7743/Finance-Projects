export type ChartRange = "1D" | "5D" | "1M" | "6M" | "1Y" | "5Y";
export type ChartType = "candles" | "line";

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
}

export interface HistoryRequestOptions {
  since?: string;
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

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      Accept: "application/json",
    },
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
  return request<HistoryResponse>(`/api/market/history?${params.toString()}`);
}

export function getQuote(symbol: string) {
  const params = new URLSearchParams({ symbol });
  return request<QuoteResponse>(`/api/market/quote?${params.toString()}`);
}
