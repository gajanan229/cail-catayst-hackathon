import { memo } from "react";
import ReactECharts from "echarts-for-react/lib/core";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import type { EChartsOption } from "echarts";

echarts.use([LineChart, GridComponent, TooltipComponent, SVGRenderer]);

export type Prediction = {
  series: Record<string, [string, number][]>;
  summary: Record<string, { from: number; to: number; max: number }>;
  horizon_s?: number;
};

export function asPrediction(value: unknown): Prediction | null {
  const p = value as Prediction | null;
  return p && p.series && p.summary ? p : null;
}

/** What-if mini chart (P1): a simulator-fork prediction for one metric over the next 10 sim-minutes. */
export const PredictionChart = memo(function PredictionChart({
  prediction,
  metric = "svc.atm.p95_ms",
  color = "#5b6fb3",
  height = 54,
}: {
  prediction: Prediction;
  metric?: string;
  color?: string;
  height?: number;
}) {
  const points = prediction.series[metric] || [];
  const option: EChartsOption = {
    animation: false,
    grid: { top: 6, right: 4, bottom: 4, left: 4 },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#ffffff",
      borderColor: "#dce2ec",
      textStyle: { color: "#172033", fontSize: 11 },
      valueFormatter: (v) => `${Math.round(Number(v))} ms`,
    },
    xAxis: { type: "category", show: false, data: points.map(([t]) => t) },
    yAxis: { type: "value", show: false, min: 0 },
    series: [
      {
        type: "line",
        data: points.map(([, v]) => v),
        showSymbol: false,
        smooth: 0.2,
        lineStyle: { color, width: 2, type: "dashed" },
        areaStyle: { color, opacity: 0.06 },
      },
    ],
  };
  const s = prediction.summary[metric];
  return (
    <div className="prediction" role="img" aria-label={s ? `Predicted ${metric} from ${s.from} to ${s.to}` : "Prediction"}>
      <ReactECharts echarts={echarts} option={option} notMerge lazyUpdate opts={{ renderer: "svg" }} style={{ height, width: "100%" }} />
      {s && (
        <p className="meta prediction-caption">
          Prediction (simulator fork, 10 min): ATM p95 {Math.round(s.from)} → {Math.round(s.to)} ms
        </p>
      )}
    </div>
  );
});
