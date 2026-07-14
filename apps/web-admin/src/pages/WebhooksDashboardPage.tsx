import { Badge, Button, Group, Select, Stack, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconRefresh } from '@tabler/icons-react';
import { useCallback, useEffect, useState } from 'react';
import { MetricGrid, PageHeader, ShellTable } from '../components/Panel';
import { api, getApiError } from '../services/api';

type Dash = {
  pending: number;
  dlq: number;
  delivered_24h: number;
  total_24h?: number;
  success_rate_24h: number;
  hooks_active?: number;
  by_status?: Record<string, number>;
  items: Array<{
    id: number;
    webhook_id: number;
    company_id?: number | null;
    company_name?: string | null;
    url?: string | null;
    event: string;
    status: string;
    attempt: number;
    max_attempts?: number;
    error?: string | null;
    next_retry_at?: string | null;
    created_at?: string | null;
  }>;
};

/** Admin B2B webhook retries / DLQ §14.5.4 */
export default function WebhooksDashboardPage() {
  const [data, setData] = useState<Dash | null>(null);
  const [companyId, setCompanyId] = useState<string | null>(null);
  const [companies, setCompanies] = useState<Array<{ id: number; name: string }>>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data: dash } = await api.get<Dash>('/admin/webhooks/deliveries/dashboard', {
        params: companyId ? { company_id: Number(companyId) } : {},
      });
      setData(dash);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    api
      .get<{ items: Array<{ id: number; name: string }> }>('/admin/companies')
      .then(({ data: c }) => setCompanies(c.items || []))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const rate = Math.round((data?.success_rate_24h ?? 1) * 1000) / 10;

  return (
    <>
      <PageHeader
        title="B2B Webhooks"
        description="Retries · DLQ · success rate 24ч (§14.5.4)"
        action={
          <Group>
            <Select
              placeholder="Все компании"
              clearable
              data={companies.map((c) => ({ value: String(c.id), label: c.name }))}
              value={companyId}
              onChange={setCompanyId}
              w={220}
            />
            <Button leftSection={<IconRefresh size={16} />} loading={loading} onClick={() => void load()}>
              Обновить
            </Button>
          </Group>
        }
      />
      <MetricGrid
        items={[
          { label: 'Pending retries', value: String(data?.pending ?? 0), color: 'orange' },
          { label: 'DLQ', value: String(data?.dlq ?? 0), color: data?.dlq ? 'red' : 'teal' },
          { label: 'Delivered 24ч', value: String(data?.delivered_24h ?? 0), color: 'teal' },
          { label: 'Success 24ч', value: `${rate}%`, color: rate >= 95 ? 'teal' : 'orange' },
          { label: 'Active hooks', value: String(data?.hooks_active ?? 0) },
        ]}
      />
      <Stack mt="md">
        <Title order={4}>Ожидают retry / DLQ</Title>
        <ShellTable
          headers={['ID', 'Company', 'Hook', 'Event', 'Status', 'Attempt', 'Next retry', 'Error']}
          rows={
            (data?.items || []).length
              ? (data?.items || []).map((d) => [
                  String(d.id),
                  d.company_name || (d.company_id != null ? `#${d.company_id}` : '—'),
                  `#${d.webhook_id}`,
                  d.event,
                  <Badge key={`s-${d.id}`} color={d.status === 'dlq' ? 'red' : 'orange'}>
                    {d.status}
                  </Badge>,
                  `${d.attempt}/${d.max_attempts ?? 10}`,
                  d.next_retry_at ? d.next_retry_at.slice(0, 19).replace('T', ' ') : '—',
                  <Text key={`e-${d.id}`} size="xs" lineClamp={2}>
                    {d.error || '—'}
                  </Text>,
                ])
              : [['—', '—', 'Нет pending/DLQ', '—', '—', '—', '—', '—']]
          }
        />
      </Stack>
    </>
  );
}
