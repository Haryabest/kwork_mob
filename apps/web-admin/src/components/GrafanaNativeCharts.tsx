import { Card, SimpleGrid, Text } from '@mantine/core';
import { useMemo } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

type Props = {
  workers: Array<{ worker_id: string; gpu_util: number; gpu_temp: number }>;
  ordersHourly: Array<{ hour: string | null; count: number }>;
};

/** Нативные графики §11.2.6 когда Grafana embed недоступен */
export function GrafanaNativeCharts({ workers, ordersHourly }: Props) {
  const ordersChart = useMemo(
    () =>
      ordersHourly.map((p) => ({
        hour: (p.hour ?? '').toString().slice(5, 16).replace('T', ' '),
        count: p.count,
      })),
    [ordersHourly],
  );

  const gpuChart = useMemo(
    () =>
      workers.map((w) => ({
        id: w.worker_id.length > 10 ? `${w.worker_id.slice(0, 8)}…` : w.worker_id,
        util: Math.round(w.gpu_util),
        temp: Math.round(w.gpu_temp),
      })),
    [workers],
  );

  if (ordersChart.length === 0 && gpuChart.length === 0) {
    return (
      <Card withBorder p="lg">
        <Text>Нет данных метрик для нативных графиков.</Text>
      </Card>
    );
  }

  return (
    <SimpleGrid cols={{ base: 1, lg: 2 }}>
      {ordersChart.length > 0 && (
        <Card withBorder p="md">
          <Text fw={600} mb="sm">
            Заказы по часам (48ч)
          </Text>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={ordersChart} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,87,184,0.12)" />
              <XAxis dataKey="hour" tick={{ fontSize: 10 }} minTickGap={24} />
              <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
              <Tooltip />
              <Line type="monotone" dataKey="count" stroke="#0057b8" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}
      {gpuChart.length > 0 && (
        <Card withBorder p="md">
          <Text fw={600} mb="sm">
            GPU util / temp (15м)
          </Text>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={gpuChart} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,87,184,0.12)" />
              <XAxis dataKey="id" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="util" fill="#0057b8" name="GPU %" radius={[4, 4, 0, 0]} />
              <Bar dataKey="temp" fill="#f57c00" name="°C" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}
    </SimpleGrid>
  );
}
