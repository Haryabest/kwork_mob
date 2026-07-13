import { useCallback, useEffect, useState } from 'react';
import { Badge, Button, Center, Group, Loader, Progress, Table, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconAlertTriangle,
  IconCash,
  IconClock,
  IconRefresh,
  IconServer,
  IconStar,
} from '@tabler/icons-react';
import { api, getApiError } from '../services/api';

type Dashboard = {
  source: string;
  generated_at?: string;
  workers: Array<{ worker_id: string; gpu_util: number; gpu_temp: number; last_seen: string }>;
  queues: Array<{ queue: string; length: number; avg_wait: number }>;
  ops: {
    orders_by_status: Record<string, number>;
    queued: number;
    processing: number;
    ewt_normal_sec: number;
    ewt_high_sec: number;
    orders_hourly: Array<{ hour: string | null; count: number }>;
  };
  finance: {
    revenue_today_rub: number;
    revenue_7d_rub: number;
    refunds_7d_rub: number;
  };
  b2b: {
    companies_active: number;
    photographers_active: number;
    top_companies: Array<{ company_id: number; orders: number; revenue_rub: number }>;
  };
  quality: {
    rating_distribution: Record<string, number>;
    rating_share_4_5: number;
    rating_total: number;
    low_rating_reasons: Array<[string, number]>;
  };
  moderation: { nsfw_blocked: number };
  pg_error?: string;
};

const TABS = [
  { id: 'ops', label: 'Операции' },
  { id: 'finance', label: 'Финансы' },
  { id: 'b2b', label: 'B2B' },
  { id: 'quality', label: 'Качество' },
  { id: 'moderation', label: 'Модерация' },
] as const;

function fmtSec(s: number) {
  if (!s) return '—';
  const m = Math.floor(s / 60);
  const sec = Math.round(s % 60);
  return m > 0 ? `${m} мин ${sec} сек` : `${sec} сек`;
}

function fmtRub(n: number) {
  return `${(n || 0).toLocaleString('ru-RU')} ₽`;
}

export default function DashboardPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]['id']>('ops');
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const { data: d } = await api.get<Dashboard>('/admin/metrics/dashboard');
      setData(d);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = window.setInterval(load, 15000);
    return () => window.clearInterval(t);
  }, [load]);

  if (loading && !data) {
    return (
      <Center py="xl">
        <Loader color="brand" />
      </Center>
    );
  }

  const ops = data?.ops;
  const fin = data?.finance;
  const share45 = Math.round((data?.quality.rating_share_4_5 ?? 0) * 100);

  return (
    <div className="vz-page">
      <div className="vz-page-header">
        <div>
          <Title order={2}>Дашборд</Title>
          <Text c="#6d6c77" size="sm" mt={6}>
            §11.2 · ClickHouse + PostgreSQL · авто-обновление 15с
          </Text>
        </div>
        <Group>
          <Badge variant="light" color="brand" radius="sm">
            {data?.source ?? '—'}
          </Badge>
          <Button leftSection={<IconRefresh size={16} />} variant="light" onClick={() => load()}>
            Обновить
          </Button>
        </Group>
      </div>

      <div className="vz-grid vz-grid-2 vz-grid-4">
        <div className="vz-surface">
          <Group justify="space-between">
            <Text size="sm" c="#6d6c77">
              В очереди
            </Text>
            <IconClock size={18} color="#0057b8" />
          </Group>
          <Text fw={700} size="xl" mt={14} className="vz-metric-value">
            {ops?.queued ?? 0}
          </Text>
          <Text size="xs" c="dimmed">
            processing: {ops?.processing ?? 0}
          </Text>
        </div>
        <div className="vz-surface">
          <Group justify="space-between">
            <Text size="sm" c="#6d6c77">
              Воркеры (CH 15м)
            </Text>
            <IconServer size={18} color="#0057b8" />
          </Group>
          <Text fw={700} size="xl" mt={14} className="vz-metric-value">
            {data?.workers.length ?? 0}
          </Text>
        </div>
        <div className="vz-surface">
          <Group justify="space-between">
            <Text size="sm" c="#6d6c77">
              Выручка сегодня
            </Text>
            <IconCash size={18} color="#0057b8" />
          </Group>
          <Text fw={700} size="xl" mt={14} className="vz-metric-value">
            {fmtRub(fin?.revenue_today_rub ?? 0)}
          </Text>
        </div>
        <div className="vz-surface">
          <Group justify="space-between">
            <Text size="sm" c="#6d6c77">
              NSFW / оценки ≥4
            </Text>
            <IconAlertTriangle size={18} color="#0057b8" />
          </Group>
          <Text fw={700} size="xl" mt={14} className="vz-metric-value">
            {data?.moderation.nsfw_blocked ?? 0} / {share45}%
          </Text>
        </div>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.55rem' }}>
        {TABS.map((t) => {
          const on = t.id === tab;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              style={{
                border: on ? 'none' : '1px solid rgba(0,87,184,0.14)',
                background: on
                  ? 'linear-gradient(135deg, #0057b8 0%, #0381E9 45%, #9403fd 100%)'
                  : '#fff',
                color: on ? '#fff' : '#374151',
                borderRadius: 999,
                padding: '0.55rem 1.05rem',
                fontWeight: 600,
                fontSize: '0.875rem',
                cursor: 'pointer',
                minHeight: 44,
                fontFamily: 'inherit',
              }}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      {tab === 'ops' && (
        <div className="vz-grid vz-grid-2-lg">
          <div className="vz-surface">
            <Text fw={600}>EWT очереди</Text>
            <Text mt="md">normal: {fmtSec(ops?.ewt_normal_sec ?? 0)}</Text>
            <Text>high: {fmtSec(ops?.ewt_high_sec ?? 0)}</Text>
            <Text fw={600} mt="lg">
              Статусы заказов
            </Text>
            <Table mt="sm" withTableBorder>
              <Table.Tbody>
                {Object.entries(ops?.orders_by_status ?? {}).map(([k, v]) => (
                  <Table.Tr key={k}>
                    <Table.Td>{k}</Table.Td>
                    <Table.Td>{v}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </div>
          <div className="vz-surface">
            <Text fw={600}>Загрузка GPU (ClickHouse)</Text>
            {(data?.workers ?? []).length === 0 ? (
              <Text c="dimmed" mt="md">
                Нет метрик за 15 мин
              </Text>
            ) : (
              (data?.workers ?? []).map((w) => (
                <div key={w.worker_id} style={{ marginTop: 12 }}>
                  <Group justify="space-between">
                    <Text size="sm">{w.worker_id}</Text>
                    <Text size="sm">
                      {Math.round(w.gpu_util)}% · {Math.round(w.gpu_temp)}°C
                    </Text>
                  </Group>
                  <Progress
                    value={Math.min(100, w.gpu_util)}
                    color={w.gpu_temp > 80 ? 'red' : w.gpu_temp > 75 ? 'yellow' : 'brand'}
                    mt={4}
                  />
                </div>
              ))
            )}
            <Text fw={600} mt="lg">
              Очереди Redis (CH)
            </Text>
            {(data?.queues ?? []).map((q) => (
              <Text key={q.queue} mt={4}>
                {q.queue}: {q.length} (avg wait {fmtSec(q.avg_wait)})
              </Text>
            ))}
            <Text fw={600} mt="lg">
              Поступление (48ч)
            </Text>
            <Text size="sm" c="dimmed">
              точек: {(ops?.orders_hourly ?? []).length}
            </Text>
          </div>
        </div>
      )}

      {tab === 'finance' && (
        <div className="vz-grid vz-grid-2-lg">
          <div className="vz-surface">
            <Text fw={600}>Выручка 7 дней</Text>
            <Text size="xl" fw={700} mt="md" className="vz-metric-value">
              {fmtRub(fin?.revenue_7d_rub ?? 0)}
            </Text>
          </div>
          <div className="vz-surface">
            <Text fw={600}>Возвраты 7 дней</Text>
            <Text size="xl" fw={700} mt="md" className="vz-metric-value">
              {fmtRub(fin?.refunds_7d_rub ?? 0)}
            </Text>
          </div>
        </div>
      )}

      {tab === 'b2b' && (
        <div className="vz-grid vz-grid-2-lg">
          <div className="vz-surface">
            <Text fw={600}>Активные компании</Text>
            <Text size="xl" fw={700} mt="md">
              {data?.b2b.companies_active ?? 0}
            </Text>
            <Text mt="sm">Photographer: {data?.b2b.photographers_active ?? 0}</Text>
          </div>
          <div className="vz-surface">
            <Text fw={600}>Топ компаний (7д)</Text>
            <Table mt="sm" withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Заказы</Table.Th>
                  <Table.Th>Выручка</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {(data?.b2b.top_companies ?? []).map((c) => (
                  <Table.Tr key={c.company_id}>
                    <Table.Td>{c.company_id}</Table.Td>
                    <Table.Td>{c.orders}</Table.Td>
                    <Table.Td>{fmtRub(c.revenue_rub)}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </div>
        </div>
      )}

      {tab === 'quality' && (
        <div className="vz-grid vz-grid-2-lg">
          <div className="vz-surface">
            <Group>
              <IconStar size={18} />
              <Text fw={600}>Оценки 1–5 (доля ≥4: {share45}%, цель ≥80%)</Text>
            </Group>
            <Progress value={share45} mt="md" color={share45 >= 80 ? 'teal' : 'orange'} />
            <Table mt="md" withTableBorder>
              <Table.Tbody>
                {Object.entries(data?.quality.rating_distribution ?? {}).map(([k, v]) => (
                  <Table.Tr key={k}>
                    <Table.Td>{k}★</Table.Td>
                    <Table.Td>{v}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
            <Text size="sm" c="dimmed" mt="sm">
              всего: {data?.quality.rating_total ?? 0}
            </Text>
          </div>
          <div className="vz-surface">
            <Text fw={600}>Причины низких оценок</Text>
            {(data?.quality.low_rating_reasons ?? []).length === 0 ? (
              <Text c="dimmed" mt="md">
                Нет данных
              </Text>
            ) : (
              (data?.quality.low_rating_reasons ?? []).map(([r, n]) => (
                <Text key={r} mt={6}>
                  {r}: {n}
                </Text>
              ))
            )}
          </div>
        </div>
      )}

      {tab === 'moderation' && (
        <div className="vz-surface">
          <Text fw={600}>NSFW-блокировки (заказы)</Text>
          <Text size="xl" fw={700} mt="md">
            {data?.moderation.nsfw_blocked ?? 0}
          </Text>
        </div>
      )}

      {data?.pg_error && (
        <Text c="red" size="sm" mt="md">
          PG: {data.pg_error}
        </Text>
      )}
    </div>
  );
}
