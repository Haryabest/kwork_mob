import {
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

const COLORS = ['#0057b8', '#0381E9', '#0b7a73', '#e67700', '#c92a2a'];

export type GpuHistoryPoint = {
  t: string;
  values: Record<string, number>;
};

type Props = {
  history: GpuHistoryPoint[];
  height?: number;
};

export function WorkerGpuLineChart({ history, height = 280 }: Props) {
  const workerIds = Array.from(new Set(history.flatMap((p) => Object.keys(p.values))));

  const data = {
    labels: history.map((p) => p.t),
    datasets: workerIds.map((id, i) => {
      const color = COLORS[i % COLORS.length];
      const label = id.length > 16 ? `${id.slice(0, 14)}…` : id;
      return {
        label,
        data: history.map((p) => p.values[id] ?? null),
        borderColor: color,
        backgroundColor: `${color}22`,
        tension: 0.35,
        fill: true,
        pointRadius: 0,
        pointHoverRadius: 4,
        borderWidth: 2,
      };
    }),
  };

  return (
    <div style={{ height }}>
      <Line
        data={data}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: {
              position: 'top',
              labels: { boxWidth: 12, font: { size: 11 } },
            },
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y ?? '—'}%`,
              },
            },
          },
          scales: {
            x: {
              grid: { color: 'rgba(0,87,184,0.08)' },
              ticks: { maxTicksLimit: 8, font: { size: 10 } },
            },
            y: {
              min: 0,
              max: 100,
              grid: { color: 'rgba(0,87,184,0.08)' },
              ticks: { callback: (v) => `${v}%`, font: { size: 10 } },
            },
          },
        }}
      />
    </div>
  );
}
