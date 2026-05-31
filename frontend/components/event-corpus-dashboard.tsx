"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  Brain,
  CalendarDays,
  CandlestickChart,
  Database,
  ExternalLink,
  FileText,
  Search,
  Server,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  EventApiRequestError,
  getTrumpEvents,
  getEventsApiBaseUrl,
  type EventListResponse,
  type EventSourceFilter,
  type TrumpEventRecord,
} from "@/lib/events-api";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 30;
const sourceOptions: Array<{ value: EventSourceFilter; label: string }> = [
  { value: "all", label: "All" },
  { value: "trump_fm", label: "Social posts" },
  { value: "whitehouse", label: "White House" },
];

interface EventError {
  title: string;
  message: string;
  details: string[];
}

function describeError(err: unknown): EventError {
  if (err instanceof EventApiRequestError) {
    return {
      title: "Event corpus request failed",
      message: err.message,
      details: [
        `Request: ${err.method} ${err.url}`,
        err.status ? `HTTP status: ${err.status}` : null,
        err.detail ? `Detail: ${err.detail}` : null,
        err.isNetworkError
          ? "Likely causes: backend is stopped, wrong NEXT_PUBLIC_API_URL, or the browser cannot reach 127.0.0.1:8000."
          : null,
      ].filter((item): item is string => Boolean(item)),
    };
  }

  return {
    title: "Event corpus request failed",
    message: err instanceof Error ? err.message : "Unknown error.",
    details: [`Configured backend: ${getEventsApiBaseUrl()}`],
  };
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "n/a";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

function sourceLabel(source: string) {
  if (source === "trump_fm") {
    return "trump.fm";
  }
  if (source === "whitehouse") {
    return "White House";
  }
  return source;
}

function eventTitle(event: TrumpEventRecord) {
  const title = event.metadata.title;
  if (typeof title === "string" && title.trim()) {
    return title;
  }
  if (event.source === "trump_fm") {
    const platform = event.metadata.platform;
    return `${typeof platform === "string" ? platform : "social"} post`;
  }
  return event.event_type.replaceAll("_", " ");
}

function truncate(text: string, maxLength = 420) {
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength).trim()}...`;
}

function latestMonths(byMonth: Record<string, number>) {
  return Object.entries(byMonth)
    .sort(([left], [right]) => right.localeCompare(left))
    .slice(0, 8);
}

function EventCard({ event }: { event: TrumpEventRecord }) {
  const wordCount = event.metadata.word_count;
  const platform = event.metadata.platform;

  return (
    <Card className="border-zinc-900 bg-zinc-950/80">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-500">
              <span className="rounded-full border border-zinc-800 px-2 py-1 text-zinc-300">
                {sourceLabel(event.source)}
              </span>
              <span>{formatDateTime(event.utc_timestamp)}</span>
              {typeof platform === "string" ? <span>Platform: {platform}</span> : null}
              {typeof wordCount === "number" ? <span>{formatNumber(wordCount)} words</span> : null}
            </div>
            <CardTitle className="mt-3 text-base text-zinc-100">{eventTitle(event)}</CardTitle>
            <CardDescription className="mt-1 font-mono text-xs">{event.event_id}</CardDescription>
          </div>
          {event.url ? (
            <a
              className="inline-flex items-center gap-1 rounded-lg border border-zinc-800 px-3 py-2 text-xs text-zinc-300 hover:border-zinc-600 hover:text-zinc-50"
              href={event.url}
              rel="noreferrer"
              target="_blank"
            >
              Source
              <ExternalLink className="h-3 w-3" />
            </a>
          ) : null}
        </div>
      </CardHeader>
      <CardContent>
        <p className="whitespace-pre-wrap text-sm leading-6 text-zinc-300">{truncate(event.text)}</p>
      </CardContent>
    </Card>
  );
}

export function EventCorpusDashboard() {
  const [source, setSource] = useState<EventSourceFilter>("all");
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<EventListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<EventError | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadEvents() {
      setIsLoading(true);
      setError(null);
      try {
        const result = await getTrumpEvents({
          source,
          q: submittedQuery,
          from: fromDate || undefined,
          to: toDate || undefined,
          limit: PAGE_SIZE,
          offset,
        });
        if (!cancelled) {
          setData(result);
        }
      } catch (err) {
        if (!cancelled) {
          setError(describeError(err));
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    loadEvents();
    return () => {
      cancelled = true;
    };
  }, [fromDate, offset, source, submittedQuery, toDate]);

  const monthRows = useMemo(() => latestMonths(data?.summary.by_month ?? {}), [data]);
  const currentStart = data ? Math.min(data.offset + 1, data.total_matching) : 0;
  const currentEnd = data ? Math.min(data.offset + data.events.length, data.total_matching) : 0;

  function applySearch() {
    setOffset(0);
    setSubmittedQuery(query.trim());
  }

  function resetFilters() {
    setSource("all");
    setQuery("");
    setSubmittedQuery("");
    setFromDate("");
    setToDate("");
    setOffset(0);
  }

  return (
    <div className="min-h-screen bg-black text-zinc-50">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-zinc-900 bg-zinc-950/80 p-6 lg:block">
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-zinc-100 p-2 text-zinc-950">
            <CandlestickChart className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold">Quant Platform</p>
            <p className="text-xs text-zinc-500">Event corpus</p>
          </div>
        </div>

        <nav className="mt-10 space-y-2 text-sm">
          <Link className="flex items-center gap-2 rounded-lg px-3 py-2 text-zinc-500" href="/">
            <BarChart3 className="h-4 w-4" />
            Market Data
          </Link>
          <Link className="flex items-center gap-2 rounded-lg px-3 py-2 text-zinc-500" href="/research">
            <Activity className="h-4 w-4" />
            Research
          </Link>
          <Link
            className="flex items-center gap-2 rounded-lg bg-zinc-900 px-3 py-2 text-zinc-50"
            href="/events"
          >
            <Database className="h-4 w-4" />
            Event Corpus
          </Link>
          <span className="flex items-center gap-2 rounded-lg px-3 py-2 text-zinc-600">
            <Brain className="h-4 w-4" />
            Gemini Review
          </span>
          <span className="flex items-center gap-2 rounded-lg px-3 py-2 text-zinc-600">
            <Server className="h-4 w-4" />
            Execution
          </span>
        </nav>
      </aside>

      <main className="lg:pl-64">
        <section className="mx-auto max-w-7xl px-6 py-8">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm text-zinc-500">Local JSONL corpus</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight">
                Trump Event Corpus
              </h1>
              <p className="mt-2 max-w-3xl text-sm text-zinc-400">
                Browse the two-year pull before we add market labels. This view reads the
                local corpus only; it does not run analysis or trading logic.
              </p>
            </div>
            <Link className="text-sm text-zinc-400 hover:text-zinc-100" href="/research">
              Back to research
            </Link>
          </div>

          {error ? (
            <Card className="mb-6 border-red-900/60 bg-red-950/30">
              <CardHeader>
                <CardTitle className="text-red-200">{error.title}</CardTitle>
                <CardDescription className="text-red-200/80">{error.message}</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1 text-xs text-red-100/80">
                  {error.details.map((detail) => (
                    <li key={detail}>{detail}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Card className="border-zinc-900 bg-zinc-950/80">
              <CardHeader className="pb-2">
                <CardDescription>Total events</CardDescription>
                <CardTitle className="text-3xl">
                  {formatNumber(data?.summary.count ?? 0)}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-zinc-500">
                {data?.summary.oldest ? `${formatDateTime(data.summary.oldest)} to ${formatDateTime(data.summary.newest)}` : "No local corpus found"}
              </CardContent>
            </Card>
            <Card className="border-zinc-900 bg-zinc-950/80">
              <CardHeader className="pb-2">
                <CardDescription>Social posts</CardDescription>
                <CardTitle className="text-3xl">
                  {formatNumber(data?.summary.by_source.trump_fm ?? 0)}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-zinc-500">trump.fm, reposts skipped</CardContent>
            </Card>
            <Card className="border-zinc-900 bg-zinc-950/80">
              <CardHeader className="pb-2">
                <CardDescription>Official transcripts</CardDescription>
                <CardTitle className="text-3xl">
                  {formatNumber(data?.summary.by_source.whitehouse ?? 0)}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-zinc-500">White House sitemap/articles</CardContent>
            </Card>
            <Card className="border-zinc-900 bg-zinc-950/80">
              <CardHeader className="pb-2">
                <CardDescription>Matching filter</CardDescription>
                <CardTitle className="text-3xl">
                  {formatNumber(data?.total_matching ?? 0)}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-zinc-500">
                Showing {currentStart}-{currentEnd}
              </CardContent>
            </Card>
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
            <Card className="border-zinc-900 bg-zinc-950/80">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Search className="h-5 w-5" />
                  Filters
                </CardTitle>
                <CardDescription>Search text, narrow source, or constrain timestamps.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  {sourceOptions.map((option) => (
                    <Button
                      key={option.value}
                      className={cn(
                        source === option.value
                          ? "bg-zinc-100 text-zinc-950 hover:bg-zinc-200"
                          : "border-zinc-800 bg-zinc-950 text-zinc-400 hover:bg-zinc-900",
                      )}
                      onClick={() => {
                        setSource(option.value);
                        setOffset(0);
                      }}
                      size="sm"
                      variant={source === option.value ? "default" : "outline"}
                    >
                      {option.label}
                    </Button>
                  ))}
                </div>

                <div className="grid gap-3 md:grid-cols-[1fr_auto]">
                  <Input
                    className="border-zinc-800 bg-zinc-950 text-zinc-100"
                    onChange={(event) => setQuery(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        applySearch();
                      }
                    }}
                    placeholder="Search corpus: tariff, Tesla, China, oil..."
                    value={query}
                  />
                  <Button onClick={applySearch}>Search</Button>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <label className="space-y-2 text-sm text-zinc-400">
                    <span className="flex items-center gap-2">
                      <CalendarDays className="h-4 w-4" />
                      From
                    </span>
                    <Input
                      className="border-zinc-800 bg-zinc-950 text-zinc-100"
                      onChange={(event) => {
                        setFromDate(event.target.value);
                        setOffset(0);
                      }}
                      type="date"
                      value={fromDate}
                    />
                  </label>
                  <label className="space-y-2 text-sm text-zinc-400">
                    <span className="flex items-center gap-2">
                      <CalendarDays className="h-4 w-4" />
                      To
                    </span>
                    <Input
                      className="border-zinc-800 bg-zinc-950 text-zinc-100"
                      onChange={(event) => {
                        setToDate(event.target.value);
                        setOffset(0);
                      }}
                      type="date"
                      value={toDate}
                    />
                  </label>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-zinc-500">
                  <span>
                    Manifest updated: {formatDateTime(data?.summary.manifest_updated_at)}
                  </span>
                  <Button
                    className="border-zinc-800 bg-zinc-950 text-zinc-400 hover:bg-zinc-900"
                    onClick={resetFilters}
                    size="sm"
                    variant="outline"
                  >
                    Reset filters
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card className="border-zinc-900 bg-zinc-950/80">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Recent Monthly Coverage
                </CardTitle>
                <CardDescription>Latest months in the merged corpus.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {monthRows.map(([month, count]) => (
                    <div key={month} className="flex items-center justify-between text-sm">
                      <span className="text-zinc-400">{month}</span>
                      <span className="font-mono text-zinc-100">{formatNumber(count)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <section className="mt-6 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Events</h2>
                <p className="text-sm text-zinc-500">
                  {isLoading
                    ? "Loading local corpus..."
                    : `Showing ${currentStart}-${currentEnd} of ${formatNumber(data?.total_matching ?? 0)} matches`}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  className="border-zinc-800 bg-zinc-950 text-zinc-400 hover:bg-zinc-900"
                  disabled={!data || offset === 0 || isLoading}
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                  size="sm"
                  variant="outline"
                >
                  Previous
                </Button>
                <Button
                  className="border-zinc-800 bg-zinc-950 text-zinc-400 hover:bg-zinc-900"
                  disabled={!data?.has_more || isLoading}
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                  size="sm"
                  variant="outline"
                >
                  Next
                </Button>
              </div>
            </div>

            {data?.events.map((event) => <EventCard event={event} key={event.event_id} />)}

            {!isLoading && data?.events.length === 0 ? (
              <Card className="border-zinc-900 bg-zinc-950/80">
                <CardContent className="py-10 text-center text-sm text-zinc-500">
                  No events matched those filters.
                </CardContent>
              </Card>
            ) : null}
          </section>
        </section>
      </main>
    </div>
  );
}
