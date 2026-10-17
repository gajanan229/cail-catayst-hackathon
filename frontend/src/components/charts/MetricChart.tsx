import { memo, useEffect, useRef, useState } from "react";
import ReactECharts from "echarts-for-react/lib/core";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  MarkAreaComponent,
  MarkLineComponent,
} from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import type { EChartsOption } from "echarts";
import type { MetricPoint } from "@/api/types";
import { time } from "@/lib/utils";
echarts.use([
  LineChart,
  GridComponent,
  TooltipComponent,
  MarkAreaComponent,
  MarkLineComponent,
  SVGRenderer,
]);

type ChartProps = {
  points: MetricPoint[];
  band?: [number, number];
  color?: string;
  height?: number;
  axes?: boolean;
  markers?: { time: string; label: string }[];
};

// Keep ingestion lossless while limiting visual chart work to two updates per second.
export const MetricChart = memo(function MetricChart(props: ChartProps) {
  const latest = useRef(props);
  latest.current = props;
  const [snapshot, setSnapshot] = useState(props);
  useEffect(() => {
    const timer = setInterval(() => setSnapshot(latest.current), 500);
    return () => clearInterval(timer);
  }, []);
  return <ChartView {...snapshot} />;
});

const ChartView = memo(function ChartView({
  points,
  band,
  color = "#3FB950",
  height = 85,
  axes = false,
  markers = [],
}: ChartProps) {
  const option: EChartsOption = {
    animationDuration: 200,
    animationDurationUpdate: 200,
    textStyle: { fontFamily: "Inter" },
    grid: {
      top: axes ? 25 : 8,
      right: axes ? 16 : 2,
      bottom: axes ? 25 : 4,
      left: axes ? 45 : 2,
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#151C25",
      borderColor: "#222D3A",
      textStyle: { color: "#E6EDF3", fontSize: 12 },
    },
    xAxis: {
      type: "time",
      show: axes,
      axisLabel: {
        color: "#8A97A8",
        fontSize: 10,
        formatter: (value: number) =>
          time(new Date(value).toISOString()).slice(0, 5),
      },
      axisLine: { lineStyle: { color: "#222D3A" } },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      show: axes,
      min: band ? 0 : undefined,
      axisLabel: { color: "#8A97A8", fontSize: 10 },
      splitLine: {
        show: axes,
        lineStyle: { color: "#222D3A", type: "dashed" },
      },
    },
    series: [
      {
        type: "line",
        data: points.map(([t, v]) => [t, v]),
        showSymbol: false,
        smooth: 0.25,
        lineStyle: { color, width: 2 },
        itemStyle: { color },
        areaStyle: { color, opacity: 0.045 },
        markArea: band
          ? {
              silent: true,
              itemStyle: { color: "rgba(63,185,80,0.075)" },
              data: [[{ yAxis: band[0] }, { yAxis: band[1] }]],
            }
          : undefined,
        markLine: markers.length
          ? {
              symbol: "none",
              lineStyle: { color: "#A78BFA", type: "dashed" },
              label: { fontSize: 9, color: "#A78BFA", formatter: "{b}" },
              data: markers.map((m) => ({ name: m.label, xAxis: m.time })),
            }
          : undefined,
      },
    ],
  };
  return (
    <div
      className="metric-chart"
      role="img"
      aria-label={`Metric history${band ? `, normal band ${band[0]} to ${band[1]}` : ""}`}
    >
      <ReactECharts
        echarts={echarts}
        option={option}
        notMerge
        lazyUpdate
        opts={{ renderer: "svg" }}
        style={{ height, width: "100%" }}
      />
    </div>
  );
});
