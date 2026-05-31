"use client";

import {
  CandlestickSeries,
  ColorType,
  createChart,
  HistogramSeries,
  LineSeries,
  type CandlestickData,
  type HistogramData,
  type LineData,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import { useEffect, useRef } from "react";

import type { ChartType, IndicatorSeries, OHLCVBar } from "@/lib/api";

interface PriceChartProps {
  data: OHLCVBar[];
  indicators: IndicatorSeries[];
  type: ChartType;
}

function parseChartTime(value: string): Time {
  if (value.includes("T")) {
    return Math.floor(new Date(value).getTime() / 1000) as UTCTimestamp;
  }

  return value as Time;
}

export function PriceChart({ data, indicators, type }: PriceChartProps) {
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

    const configuredOscillatorScales = new Set<string>();
    for (const indicator of indicators) {
      for (const line of indicator.lines) {
        const isOscillator = indicator.pane === "oscillator";
        const priceScaleId = isOscillator ? `oscillator-${indicator.id}` : "right";

        if (line.style === "histogram") {
          const histogramSeries = chart.addSeries(HistogramSeries, {
            priceScaleId,
            color: line.color,
            base: 0,
          });
          const histogramData: HistogramData[] = line.points.map((point) => ({
            time: parseChartTime(point.time),
            value: point.value,
            color: point.value >= 0 ? "#22c55e" : "#ef4444",
          }));
          histogramSeries.setData(histogramData);
        } else {
          const indicatorSeries = chart.addSeries(LineSeries, {
            priceScaleId,
            color: line.color,
            lineWidth: 2,
            lastValueVisible: false,
            priceLineVisible: false,
          });
          const indicatorData: LineData[] = line.points.map((point) => ({
            time: parseChartTime(point.time),
            value: point.value,
          }));
          indicatorSeries.setData(indicatorData);
        }

        if (isOscillator && !configuredOscillatorScales.has(priceScaleId)) {
          chart.priceScale(priceScaleId).applyOptions({
            scaleMargins: {
              top: 0.74,
              bottom: 0.02,
            },
            visible: false,
          });
          configuredOscillatorScales.add(priceScaleId);
        }
      }
    }

    chart.timeScale().fitContent();

    return () => {
      chart.remove();
    };
  }, [data, indicators, type]);

  if (data.length === 0) {
    return (
      <div className="flex h-[420px] items-center justify-center rounded-lg border border-dashed border-zinc-800 text-sm text-zinc-500">
        No chart data loaded yet.
      </div>
    );
  }

  return <div ref={containerRef} className="h-[420px] w-full" />;
}
