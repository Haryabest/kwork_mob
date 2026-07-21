import { useCallback, useEffect, useState } from 'react';
import { Button, Card, Center, Group, Loader, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { Link } from 'react-router-dom';
import { GrafanaNativeCharts } from '../components/GrafanaNativeCharts';
import { api, getApiError } from '../services/api';

type DashboardFallback = {
  workers: Array<{ worker_id: string; gpu_util: number; gpu_temp: number }>;
  ops: { orders_hourly: Array<{ hour: string | null; count: number }> };
};

export default function GrafanaPage() {
  const [url, setUrl] = useState<string | null>(null);
  const [fallback, setFallback] = useState<DashboardFallback | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [embedRes, dashRes] = await Promise.all([
        api.get<{ embed_url: string | null; configured: boolean }>('/admin/grafana/embed'),
        api.get<DashboardFallback>('/admin/metrics/dashboard'),
      ]);
      setUrl(embedRes.data.embed_url);
      setFallback(dashRes.data);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  return (
    <div className="vz-page">
      <Group justify="space-between" mb="md">
        <div>
          <Title order={2}>Grafana</Title>
          <Text c="#6d6c77" size="sm">
            Мониторинг §11.1 — задайте GRAFANA_EMBED_URL. Интерактивные графики KPI — в{' '}
            <Text component={Link} to="/" size="sm" c="brand">
              Дашборде §11.2.6
            </Text>
            .
          </Text>
        </div>
        <Button variant="light" onClick={() => void load()}>
          Обновить
        </Button>
      </Group>
      {url ? (
        <iframe
          title="Grafana"
          src={url}
          style={{ width: '100%', height: 'calc(100vh - 140px)', border: 0, borderRadius: 8 }}
        />
      ) : (
        <>
          <Card withBorder p="lg" mb="md">
            <Text mb="sm">Grafana embed URL не настроен (GRAFANA_EMBED_URL).</Text>
            <Text size="sm" c="dimmed">
              Ниже — нативные интерактивные графики из ClickHouse/PostgreSQL §11.2.6.
            </Text>
          </Card>
          <GrafanaNativeCharts
            workers={fallback?.workers ?? []}
            ordersHourly={fallback?.ops.orders_hourly ?? []}
          />
        </>
      )}
    </div>
  );
}
