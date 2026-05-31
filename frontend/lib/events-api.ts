const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export function getEventsApiBaseUrl() {
  return API_URL;
}

export class EventApiRequestError extends Error {
  url: string;
  method: string;
  status?: number;
  detail?: string;
  body?: string;
  isNetworkError: boolean;

  constructor({
    message,
    url,
    method,
    status,
    detail,
    body,
    isNetworkError = false,
  }: {
    message: string;
    url: string;
    method: string;
    status?: number;
    detail?: string;
    body?: string;
    isNetworkError?: boolean;
  }) {
    super(message);
    this.name = "EventApiRequestError";
    this.url = url;
    this.method = method;
    this.status = status;
    this.detail = detail;
    this.body = body;
    this.isNetworkError = isNetworkError;
  }
}

export type EventSourceFilter = "all" | "trump_fm" | "whitehouse";

export interface EventSummary {
  exists: boolean;
  count: number;
  by_source: Record<string, number>;
  by_month: Record<string, number>;
  oldest?: string | null;
  newest?: string | null;
  manifest_updated_at?: string | null;
}

export interface TrumpEventRecord {
  event_id: string;
  utc_timestamp: string;
  source: string;
  event_type: string;
  text: string;
  url?: string | null;
  native_id: string;
  metadata: Record<string, unknown>;
}

export interface EventListResponse {
  summary: EventSummary;
  events: TrumpEventRecord[];
  total_matching: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

async function requestEvents(path: string): Promise<EventListResponse> {
  const url = `${API_URL}${path}`;
  let response: Response;

  try {
    response = await fetch(url, {
      headers: {
        Accept: "application/json",
      },
    });
  } catch (err) {
    const detail = err instanceof Error ? err.message : "Unknown browser fetch error";
    throw new EventApiRequestError({
      message: `Could not reach backend at ${url}.`,
      url,
      method: "GET",
      detail,
      isNetworkError: true,
    });
  }

  const bodyText = await response.text();
  if (!response.ok) {
    let message = bodyText || `Request failed with status ${response.status}`;
    let detail: string | undefined;
    try {
      const parsed = JSON.parse(bodyText) as { detail?: unknown };
      if (typeof parsed.detail === "string") {
        message = parsed.detail;
        detail = parsed.detail;
      }
    } catch {
      // Keep raw body text when the API did not return JSON.
    }
    throw new EventApiRequestError({
      message,
      url,
      method: "GET",
      status: response.status,
      detail,
      body: bodyText,
    });
  }

  return JSON.parse(bodyText) as EventListResponse;
}

export function getTrumpEvents(
  options: {
    source?: EventSourceFilter;
    q?: string;
    from?: string;
    to?: string;
    limit?: number;
    offset?: number;
  } = {},
) {
  const params = new URLSearchParams();
  if (options.source && options.source !== "all") {
    params.set("source", options.source);
  }
  if (options.q?.trim()) {
    params.set("q", options.q.trim());
  }
  if (options.from) {
    params.set("from", options.from);
  }
  if (options.to) {
    params.set("to", options.to);
  }
  if (options.limit) {
    params.set("limit", String(options.limit));
  }
  if (options.offset) {
    params.set("offset", String(options.offset));
  }
  const query = params.toString();
  return requestEvents(`/api/events/trump${query ? `?${query}` : ""}`);
}
