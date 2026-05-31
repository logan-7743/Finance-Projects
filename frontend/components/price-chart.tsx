"use client";

import {
  CandlestickSeries,
  ColorType,
  createChart,
  LineSeries,
  type CandlestickData,
  type LineData,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import { useEffect, useRef } from "react";

import type { ChartType, OHLCVBar } from "@/lib/api";

interface PriceChartProps {
  data: OHLCVBar[];
  type: ChartType;
}

function parseChartTime(value: string): Time {
  if (value.includes("T")) {
    return Math.floor(new Date(value).getTime() / 1000) as UTCTimestamp;
  }

  return value as Time;
}

export function PriceChart({ data, type }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || data.length === 0) {
      return;
    }

    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "#09090b" },
        textColor: "#a1a1aa",
      },
      grid: {
        vertLines: { color: "#18181b" },
        horzLines: { color: "#18181b" },
      },
      rightPriceScale: {
        borderColor: "#27272a",
      },
      timeScale: {
        borderColor: "#27272a",
        timeVisible: true,
      },
      crosshair: {
        vertLine: { color: "#71717a" },
        horzLine: { color: "#71717a" },
      },
    });

    if (type === "candles") {
      const series = chart.addSeries(CandlestickSeries, {
        upColor: "#22c55e",
        downColor: "#ef4444",
        borderVisible: false,
        wickUpColor: "#22c55e",
        wickDownColor: "#ef4444",
      });

      const candleData: CandlestickData[] = data.map((bar) => ({
        time: parseChartTime(bar.time),
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      }));

      series.setData(candleData);
    } else {
      const series = chart.addSeries(LineSeries, {
        color: "#38bdf8",
        lineWidth: 2,
      });

      const lineData: LineData[] = data.map((bar) => ({
        time: parseChartTime(bar.time),
        value: bar.close,
      }));

      series.setData(lineData);
    }

    chart.timeScale().fitContent();

    return () => {
      chart.remove();
    };
  }, [data, type]);

  if (data.length === 0) {
    return (
      <div className="flex h-[420px] items-center justify-center rounded-lg border border-dashed border-zinc-800 text-sm text-zinc-500">
        No chart data loaded yet.
      </div>
    );
  }

  return <div ref={containerRef} className="h-[420px] w-full" />;
}
