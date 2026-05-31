import type { IndicatorKind, IndicatorRequestConfig } from "@/lib/api";

export interface IndicatorParamSpec {
  key: string;
  label: string;
  min: number;
  max: number;
  step: number;
}

export interface IndicatorSpec {
  kind: IndicatorKind;
  label: string;
  defaults: Record<string, number>;
  params: IndicatorParamSpec[];
  lineKeys: Array<{ key: string; label: string }>;
}

export const INDICATOR_SPECS: IndicatorSpec[] = [
  {
    kind: "ema",
    label: "EMA",
    defaults: { period: 20 },
    params: [{ key: "period", label: "Period", min: 2, max: 500, step: 1 }],
    lineKeys: [{ key: "ema", label: "EMA" }],
  },
  {
    kind: "sma",
    label: "SMA",
    defaults: { period: 20 },
    params: [{ key: "period", label: "Period", min: 2, max: 500, step: 1 }],
    lineKeys: [{ key: "sma", label: "SMA" }],
  },
  {
    kind: "atr",
    label: "ATR",
    defaults: { period: 14 },
    params: [{ key: "period", label: "Period", min: 2, max: 300, step: 1 }],
    lineKeys: [{ key: "atr", label: "ATR" }],
  },
  {
    kind: "adx",
    label: "ADX",
    defaults: { period: 14 },
    params: [{ key: "period", label: "Period", min: 2, max: 300, step: 1 }],
    lineKeys: [
      { key: "adx", label: "ADX" },
      { key: "plus_di", label: "+DI" },
      { key: "minus_di", label: "-DI" },
    ],
  },
  {
    kind: "rsi",
    label: "RSI",
    defaults: { period: 14 },
    params: [{ key: "period", label: "Period", min: 2, max: 300, step: 1 }],
    lineKeys: [{ key: "rsi", label: "RSI" }],
  },
  {
    kind: "macd",
    label: "MACD",
    defaults: { fast: 12, slow: 26, signal: 9 },
    params: [
      { key: "fast", label: "Fast", min: 2, max: 200, step: 1 },
      { key: "slow", label: "Slow", min: 3, max: 300, step: 1 },
      { key: "signal", label: "Signal", min: 2, max: 100, step: 1 },
    ],
    lineKeys: [
      { key: "macd", label: "MACD" },
      { key: "signal", label: "Signal" },
      { key: "histogram", label: "Histogram" },
    ],
  },
  {
    kind: "bollinger",
    label: "Bollinger Bands",
    defaults: { period: 20, stddev: 2 },
    params: [
      { key: "period", label: "Period", min: 2, max: 300, step: 1 },
      { key: "stddev", label: "StdDev", min: 0.1, max: 6, step: 0.1 },
    ],
    lineKeys: [
      { key: "upper", label: "Upper" },
      { key: "basis", label: "Basis" },
      { key: "lower", label: "Lower" },
    ],
  },
  {
    kind: "vwap",
    label: "VWAP",
    defaults: {},
    params: [],
    lineKeys: [{ key: "vwap", label: "VWAP" }],
  },
  {
    kind: "stochastic",
    label: "Stochastic",
    defaults: { period: 14, smooth: 3 },
    params: [
      { key: "period", label: "Period", min: 2, max: 300, step: 1 },
      { key: "smooth", label: "Smooth", min: 1, max: 50, step: 1 },
    ],
    lineKeys: [
      { key: "k", label: "%K" },
      { key: "d", label: "%D" },
    ],
  },
  {
    kind: "obv",
    label: "OBV",
    defaults: {},
    params: [],
    lineKeys: [{ key: "obv", label: "OBV" }],
  },
];

export const INDICATOR_SPECS_BY_KIND: Record<IndicatorKind, IndicatorSpec> =
  INDICATOR_SPECS.reduce(
    (acc, spec) => {
      acc[spec.kind] = spec;
      return acc;
    },
    {} as Record<IndicatorKind, IndicatorSpec>,
  );

export function createIndicatorConfig(
  kind: IndicatorKind,
  id: string,
): IndicatorRequestConfig {
  const spec = INDICATOR_SPECS_BY_KIND[kind];
  return {
    id,
    kind,
    params: { ...spec.defaults },
  };
}
