import * as echarts from "echarts";
import { useEffect, useRef } from "react";

export function EChart({ option, height = 300 }: { option: echarts.EChartsOption; height?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const container = ref.current;
    let chart: echarts.ECharts | null = null;
    const resize = () => {
      if (!container.clientWidth || !container.clientHeight) return;
      if (!chart) {
        chart = echarts.init(container, "dark");
        chart.setOption({ backgroundColor: "transparent", ...option });
      }
      chart.resize();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(container);
    resize();
    return () => {
      observer.disconnect();
      chart?.dispose();
    };
  }, [JSON.stringify(option)]);
  return <div ref={ref} style={{ width: "100%", height }} />;
}

const AXIS = { axisLabel: { color: "#8b98a9" }, splitLine: { lineStyle: { color: "#232b38" } } };

export function RadarChart({ names, scores }: { names: string[]; scores: (number | null)[] }) {
  return (
    <EChart
      height={340}
      option={{
        radar: {
          indicator: names.map((n) => ({ name: n, max: 100 })),
          axisName: { color: "#c8d2de", fontSize: 11 },
          splitLine: { lineStyle: { color: "#2b3444" } },
          splitArea: { show: false },
        },
        series: [{
          type: "radar",
          data: [{ value: scores.map((s) => s ?? 0), areaStyle: { opacity: 0.25 }, lineStyle: { color: "#f0b90b" }, itemStyle: { color: "#f0b90b" } }],
        }],
        tooltip: {},
      }}
    />
  );
}

export function LineChart({ dates, series, log = false }: {
  dates: string[];
  series: { name: string; data: (number | null)[]; color?: string }[];
  log?: boolean;
}) {
  return (
    <EChart
      height={320}
      option={{
        tooltip: { trigger: "axis" },
        legend: { textStyle: { color: "#c8d2de" } },
        xAxis: { type: "category", data: dates, ...AXIS },
        yAxis: { type: log ? "log" : "value", ...AXIS },
        series: series.map((s) => ({
          name: s.name, type: "line", data: s.data, showSymbol: false,
          lineStyle: { width: 1.6, color: s.color }, itemStyle: { color: s.color },
        })),
      }}
    />
  );
}

export function BarChart({ cats, series }: {
  cats: string[];
  series: { name: string; data: (number | null)[]; color?: string }[];
}) {
  return (
    <EChart
      height={300}
      option={{
        tooltip: { trigger: "axis" },
        legend: { textStyle: { color: "#c8d2de" } },
        xAxis: { type: "category", data: cats, ...AXIS },
        yAxis: { type: "value", ...AXIS },
        series: series.map((s) => ({ name: s.name, type: "bar", data: s.data, itemStyle: { color: s.color } })),
      }}
    />
  );
}

export function PieChart({ data }: { data: { name: string; value: number }[] }) {
  return (
    <EChart
      height={300}
      option={{
        tooltip: {},
        legend: { textStyle: { color: "#c8d2de" } },
        series: [{ type: "pie", radius: ["40%", "70%"], data, label: { color: "#e8edf3" } }],
      }}
    />
  );
}
