import { Badge, Button, Card, Center, Group, Loader, NumberInput, Select, Stack, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconDownload, IconRefresh } from '@tabler/icons-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { MetricGrid, PageHeader, ShellTable } from '../components/Panel';
import { api, getApiError } from '../services/api';

const CHART_COLORS = ['#0381E9', '#9403fd', '#2e7d32', '#f57c00', '#c62828', '#6d6c77', '#00897b', '#5e35b1'];

type ScreenRow = { screen: string; views: number };
type ScreensData = {
  days: number;
  total_views: number;
  source: string;
  items: ScreenRow[];
};
type SyncStatus = {
  pending_ch_sync: number;
  alert: boolean;
  alert_threshold: number;
};
type RawEvent = {
  id: number;
  user_id: number;
  event: string;
  event_ts?: string;
  props?: Record<string, unknown>;
};
type TimeseriesData = {
  days: number;
  source: string;
  screens: string[];
  series: Array<Record<string, string | number>>;
};

export default function AnalyticsPage() {
  const [days, setDays] = useState('7');
  const [screens, setScreens] = useState<ScreensData | null>(null);
  const [timeseries, setTimeseries] = useState<TimeseriesData | null>(null);
  const [sync, setSync] = useState<SyncStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [userId, setUserId] = useState<number | string>('');
  const [events, setEvents] = useState<RawEvent[]>([]);
  const [eventsLoading, setEventsLoading] = useState(false);

  const load = useCallback(async () => {
    const d = Number(days) || 7;
    const [sc, st, ts] = await Promise.all([
      api.get<ScreensData>('/admin/analytics/screens', { params: { days: d } }),
      api.get<SyncStatus>('/admin/analytics/status'),
      api.get<TimeseriesData>('/admin/analytics/screens/timeseries', { params: { days: d, top: 8 } }),
    ]);
    setScreens(sc.data);
    setSync(st.data);
    setTimeseries(ts.data);
  }, [days]);

  const chartData = useMemo(
    () =>
      (timeseries?.series ?? []).map((row) => ({
        ...row,
        day: String(row.day).slice(5, 10),
      })),
    [timeseries],
  );

  useEffect(() => {
    load()
      .catch((e) => notifications.show({ color: 'red', message: getApiError(e) }))
      .finally(() => setLoading(false));
  }, [load]);

  async function runSync() {
    setSyncing(true);
    try {
      const { data } = await api.post<{ synced: number; pending: number }>('/admin/analytics/sync');
      notifications.show({
        color: 'teal',
        message: `Синхронизировано: ${data.synced}, pending: ${data.pending}`,
      });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setSyncing(false);
    }
  }

  async function loadEvents() {
    setEventsLoading(true);
    try {
      const params: Record<string, string | number> = { limit: 200 };
      if (userId !== '') params.user_id = Number(userId);
      const { data } = await api.get<{ items: RawEvent[] }>('/admin/analytics/events', { params });
      setEvents(data.items ?? []);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setEventsLoading(false);
    }
  }

  async function exportEventsCsv() {
    try {
      const params: Record<string, string | number> = { format: 'csv', limit: 2000 };
      if (userId !== '') params.user_id = Number(userId);
      const { data } = await api.get('/admin/analytics/events', {
        params,
        responseType: 'blob',
      });
      const url = URL.createObjectURL(data as Blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'analytics-events.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  async function exportScreensCsv() {
    try {
      const { data } = await api.get('/admin/analytics/screens', {
        params: { days: Number(days) || 7, format: 'csv' },
        responseType: 'blob',
      });
      const url = URL.createObjectURL(data as Blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'analytics-screens.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  if (loading) {
    return (
      <Center py="xl">
        <Loader color="brand" />
      </Center>
    );
  }

  return (
    <>
      <PageHeader
        title="Аналитика mobile"
        description="screen_view breakdown · raw events · PG→CH sync §19.20"
        action={
          <Group>
            <Button leftSection={<IconRefresh size={16} />} variant="light" onClick={() => void load()}>
              Обновить
            </Button>
            <Button loading={syncing} onClick={() => void runSync()}>
              PG→CH sync
            </Button>
          </Group>
        }
      />
      <MetricGrid
        items={[
          {
            label: 'Pending CH sync',
            value: String(sync?.pending_ch_sync ?? '—'),
            color: sync?.alert ? 'red' : 'teal',
            hint: sync?.alert ? `>${sync?.alert_threshold}` : 'OK',
          },
          { label: 'Views', value: String(screens?.total_views ?? 0), hint: `${screens?.days ?? days}д` },
          { label: 'Source', value: screens?.source ?? '—' },
          { label: 'Screens', value: String(screens?.items?.length ?? 0) },
        ]}
      />
      <Group mb="md" align="flex-end">
        <Select
          label="Период"
          data={[
            { value: '7', label: '7 дней' },
            { value: '14', label: '14 дней' },
            { value: '30', label: '30 дней' },
          ]}
          value={days}
          onChange={(v) => setDays(v || '7')}
          w={140}
        />
        <Button variant="light" leftSection={<IconDownload size={16} />} onClick={() => void exportScreensCsv()}>
          Screens CSV
        </Button>
        {sync?.alert && <Badge color="red">CH sync backlog</Badge>}
      </Group>
      {chartData.length > 0 && (
        <Card withBorder mb="md" p="md">
          <Title order={5} mb="sm">
            Screen views по дням (top {timeseries?.screens?.length ?? 0}, {timeseries?.source})
          </Title>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip />
              <Legend />
              {(timeseries?.screens ?? []).map((s, i) => (
                <Line
                  key={s}
                  type="monotone"
                  dataKey={s}
                  stroke={CHART_COLORS[i % CHART_COLORS.length]}
                  dot={false}
                  strokeWidth={2}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}
      <ShellTable
        headers={['Screen', 'Views']}
        rows={(screens?.items ?? []).map((r) => [r.screen, String(r.views)])}
      />

      <PageHeader title="Raw events" description="Фильтр по user_id · export CSV" />
      <Group mb="md" align="flex-end">
        <NumberInput
          label="User ID"
          placeholder="все"
          value={userId}
          onChange={setUserId}
          min={1}
          w={160}
        />
        <Button loading={eventsLoading} onClick={() => void loadEvents()}>
          Загрузить
        </Button>
        <Button variant="light" leftSection={<IconDownload size={16} />} onClick={() => void exportEventsCsv()}>
          Export CSV
        </Button>
      </Group>
      <ShellTable
        headers={['ID', 'User', 'Event', 'Time', 'Props']}
        rows={
          events.length
            ? events.map((e) => [
                String(e.id),
                String(e.user_id),
                e.event,
                e.event_ts?.slice(0, 19) ?? '—',
                <Text key={`p${e.id}`} size="xs" lineClamp={1}>
                  {JSON.stringify(e.props ?? {})}
                </Text>,
              ])
            : [['—', 'Нет данных', '—', '—', '—']]
        }
      />
    </>
  );
}
