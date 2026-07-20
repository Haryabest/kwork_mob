'use client';

import {
  Badge,
  Button,
  Code,
  Group,
  Modal,
  MultiSelect,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { useCallback, useEffect, useState } from 'react';
import { SellerShell } from '../../../components/SellerShell';
import { PageHeader, Surface } from '../../../components/ui';
import { api, apiMessage } from '../../../services/api';

const EVENT_OPTS = [
  'model.generated',
  'order.created',
  'order.completed',
  'order.cancelled',
  'order.failed',
  'shoot_link.uploaded',
  'balance.low',
  'member.invited',
].map((e) => ({ value: e, label: e }));

type Hook = { id: number; url: string; events: string[]; is_active: boolean };
type Delivery = {
  id: number;
  webhook_id: number;
  event: string;
  status: string;
  attempt: number;
  max_attempts?: number;
  status_code?: number | null;
  ok: boolean;
  error?: string | null;
  payload?: unknown;
  next_retry_at?: string | null;
  created_at?: string;
};

/** §14.5 Webhooks + DLQ replay */
export default function WebhooksPage() {
  const [hooks, setHooks] = useState<Hook[]>([]);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [url, setUrl] = useState('https://');
  const [secret, setSecret] = useState('');
  const [events, setEvents] = useState<string[]>(['model.generated', 'order.created']);
  const [filter, setFilter] = useState<string | null>('dlq');
  const [hookFilter, setHookFilter] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [detailOpen, detailHandlers] = useDisclosure(false);
  const [detail, setDetail] = useState<Delivery | null>(null);
  const [dash, setDash] = useState<{
    pending: number;
    dlq: number;
    delivered_24h: number;
    success_rate_24h: number;
    failed_streak_hooks?: number;
    by_status?: Record<string, number>;
  } | null>(null);

  const load = useCallback(async () => {
    const [h, d, dashRes] = await Promise.all([
      api.get<{ items: Hook[] }>('/company/webhooks'),
      api.get<{ items: Delivery[] }>('/company/webhooks/deliveries', {
        params: {
          ...(filter ? { status: filter } : {}),
          ...(hookFilter ? { webhook_id: Number(hookFilter) } : {}),
        },
      }),
      api.get<{
        pending: number;
        dlq: number;
        delivered_24h: number;
        success_rate_24h: number;
        failed_streak_hooks?: number;
        by_status?: Record<string, number>;
      }>('/company/webhooks/deliveries/dashboard').catch(() => ({ data: null })),
    ]);
    setHooks(h.data.items ?? []);
    setDeliveries(d.data.items ?? []);
    if (dashRes.data) setDash(dashRes.data);
  }, [filter, hookFilter]);

  useEffect(() => {
    load().catch((e) => notifications.show({ color: 'red', message: apiMessage(e) }));
  }, [load]);

  async function create() {
    try {
      await api.post('/company/webhooks', { url, secret, events });
      notifications.show({ color: 'teal', message: 'Webhook создан' });
      setSecret('');
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }

  async function remove(id: number) {
    try {
      await api.delete(`/company/webhooks/${id}`);
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }

  async function retry(id: number) {
    try {
      const { data } = await api.post<{ status: string }>(`/company/webhooks/deliveries/${id}/retry`);
      notifications.show({ color: 'teal', message: `Retry → ${data.status}` });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }

  async function replayAllDlq() {
    setBusy(true);
    try {
      const { data } = await api.post<{ replayed: number; delivered: number; failed: number }>(
        '/company/webhooks/deliveries/replay-dlq',
      );
      notifications.show({
        color: 'teal',
        message: `DLQ replay: ${data.delivered} ok / ${data.failed} fail из ${data.replayed}`,
      });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function openDetail(id: number) {
    try {
      const { data } = await api.get<Delivery>(`/company/webhooks/deliveries/${id}`);
      setDetail(data);
      detailHandlers.open();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }

  const dlqCount = deliveries.filter((d) => d.status === 'dlq').length;

  const failedCount = dash?.by_status?.failed ?? 0;

  return (
    <SellerShell>
      <PageHeader
        title="Webhooks + DLQ"
        description="HMAC-подписи · retry ×10 · DLQ replay (§14.5.4)"
        action={
          <Button loading={busy} onClick={() => void replayAllDlq()} disabled={filter !== 'dlq' && dlqCount === 0}>
            Replay all DLQ
          </Button>
        }
      />

      <Group mb="lg" gap="md">
        <Badge size="lg" variant="light" color="orange">
          Pending {dash?.pending ?? 0}
        </Badge>
        <Badge size="lg" variant="light" color={(dash?.dlq ?? 0) > 0 ? 'red' : 'teal'}>
          DLQ {dash?.dlq ?? 0}
        </Badge>
        <Badge size="lg" variant="light" color={failedCount > 0 ? 'red' : 'gray'}>
          Failed {failedCount}
        </Badge>
        {dash && (
          <>
            <Badge size="lg" variant="light" color="teal">
              OK 24ч {dash.delivered_24h}
            </Badge>
            <Badge size="lg" variant="light">
              Success {Math.round(dash.success_rate_24h * 1000) / 10}%
            </Badge>
            {(dash.failed_streak_hooks ?? 0) > 0 && (
              <Badge size="lg" variant="light" color="red">
                Hooks streak {dash.failed_streak_hooks}
              </Badge>
            )}
          </>
        )}
      </Group>

      <Surface mb="lg">
        <Text fw={600} mb="sm">
          Новый webhook
        </Text>
        <Stack maw={640}>
          <TextInput label="URL" value={url} onChange={(e) => setUrl(e.currentTarget.value)} />
          <TextInput
            label="Secret (HMAC-SHA256 → X-KWork-Signature)"
            value={secret}
            onChange={(e) => setSecret(e.currentTarget.value)}
          />
          <MultiSelect label="События" data={EVENT_OPTS} value={events} onChange={setEvents} />
          <Text size="xs" c="dimmed">
            Заголовки: X-KWork-Event, X-KWork-Signature, X-KWork-Delivery. Тело — JSON.
          </Text>
          <Button w="fit-content" onClick={() => void create()}>
            Добавить
          </Button>
        </Stack>
      </Surface>

      <Surface mb="lg">
        <Title order={4} mb="sm">
          Endpoints
        </Title>
        <Table withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>URL</Table.Th>
              <Table.Th>Events</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {hooks.map((h) => (
              <Table.Tr key={h.id}>
                <Table.Td>{h.id}</Table.Td>
                <Table.Td>{h.url}</Table.Td>
                <Table.Td>{(h.events || []).join(', ')}</Table.Td>
                <Table.Td>
                  <Button size="xs" color="red" variant="light" onClick={() => void remove(h.id)}>
                    Отключить
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Surface>

      <Surface>
        <Group mb="sm" justify="space-between" wrap="wrap">
          <Title order={4}>Доставки / DLQ</Title>
          <Group>
            <Select
              placeholder="Все webhooks"
              clearable
              maw={200}
              data={hooks.map((h) => ({ value: String(h.id), label: `#${h.id}` }))}
              value={hookFilter}
              onChange={setHookFilter}
            />
            {(['dlq', 'pending', 'delivered', null] as const).map((f) => (
              <Button
                key={String(f)}
                size="xs"
                variant={filter === f ? 'filled' : 'light'}
                onClick={() => setFilter(f)}
              >
                {f ?? 'Все'}
              </Button>
            ))}
          </Group>
        </Group>
        <Table withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>Hook</Table.Th>
              <Table.Th>Event</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Attempt</Table.Th>
              <Table.Th>HTTP</Table.Th>
              <Table.Th>Next retry</Table.Th>
              <Table.Th>Error</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {deliveries.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={9}>
                  <Text c="dimmed" size="sm">
                    Нет доставок
                  </Text>
                </Table.Td>
              </Table.Tr>
            ) : (
              deliveries.map((d) => (
                <Table.Tr key={d.id}>
                  <Table.Td>{d.id}</Table.Td>
                  <Table.Td>#{d.webhook_id}</Table.Td>
                  <Table.Td>{d.event}</Table.Td>
                  <Table.Td>
                    <Badge color={d.status === 'delivered' ? 'teal' : d.status === 'dlq' ? 'red' : 'orange'}>
                      {d.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    {d.attempt}/{d.max_attempts ?? 10}
                  </Table.Td>
                  <Table.Td>{d.status_code ?? '—'}</Table.Td>
                  <Table.Td>
                    <Text size="xs">
                      {d.next_retry_at ? new Date(d.next_retry_at).toLocaleString('ru-RU') : '—'}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" lineClamp={1} maw={180}>
                      {d.error || '—'}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Group gap={4} wrap="nowrap">
                      <Button size="xs" variant="light" onClick={() => void openDetail(d.id)}>
                        Payload
                      </Button>
                      {d.status !== 'delivered' && (
                        <Button size="xs" onClick={() => void retry(d.id)}>
                          Retry
                        </Button>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))
            )}
          </Table.Tbody>
        </Table>
      </Surface>

      <Modal opened={detailOpen} onClose={detailHandlers.close} title={`Delivery #${detail?.id ?? ''}`} size="lg">
        <Stack>
          <Text size="sm">
            {detail?.event} · {detail?.status} · HTTP {detail?.status_code ?? '—'}
          </Text>
          <Code block style={{ maxHeight: 360, overflow: 'auto' }}>
            {JSON.stringify(detail?.payload ?? {}, null, 2)}
          </Code>
        </Stack>
      </Modal>
    </SellerShell>
  );
}
