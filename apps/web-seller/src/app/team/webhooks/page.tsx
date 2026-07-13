'use client';

import {
  Badge,
  Button,
  Group,
  MultiSelect,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';
import { SellerShell } from '../../../components/SellerShell';
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
  ok: boolean;
  error?: string | null;
  created_at?: string;
};

export default function WebhooksPage() {
  const [hooks, setHooks] = useState<Hook[]>([]);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [url, setUrl] = useState('https://');
  const [secret, setSecret] = useState('');
  const [events, setEvents] = useState<string[]>(['model.generated', 'order.created']);
  const [filter, setFilter] = useState<string | null>('dlq');

  async function load() {
    const [h, d] = await Promise.all([
      api.get<{ items: Hook[] }>('/company/webhooks'),
      api.get<{ items: Delivery[] }>('/company/webhooks/deliveries', {
        params: filter ? { status: filter } : {},
      }),
    ]);
    setHooks(h.data.items ?? []);
    setDeliveries(d.data.items ?? []);
  }

  useEffect(() => {
    load().catch((e) => notifications.show({ color: 'red', message: apiMessage(e) }));
  }, [filter]);

  async function create() {
    try {
      await api.post('/company/webhooks', { url, secret, events });
      notifications.show({ color: 'teal', message: 'Webhook создан' });
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

  return (
    <SellerShell>
      <Title order={2} mb="md">
        Webhooks + DLQ (§14.5)
      </Title>
      <Stack maw={640} mb="xl">
        <TextInput label="URL" value={url} onChange={(e) => setUrl(e.currentTarget.value)} />
        <TextInput label="Secret (HMAC)" value={secret} onChange={(e) => setSecret(e.currentTarget.value)} />
        <MultiSelect label="События" data={EVENT_OPTS} value={events} onChange={setEvents} />
        <Button w="fit-content" onClick={create}>
          Добавить
        </Button>
      </Stack>

      <Table mb="xl" withTableBorder>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>URL</Table.Th>
            <Table.Th>Events</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {hooks.map((h) => (
            <Table.Tr key={h.id}>
              <Table.Td>{h.url}</Table.Td>
              <Table.Td>{(h.events || []).join(', ')}</Table.Td>
              <Table.Td>
                <Button size="xs" color="red" variant="light" onClick={() => remove(h.id)}>
                  Отключить
                </Button>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <Group mb="sm">
        <Title order={4}>Доставки / DLQ</Title>
        <Button size="xs" variant={filter === 'dlq' ? 'filled' : 'light'} onClick={() => setFilter('dlq')}>
          DLQ
        </Button>
        <Button size="xs" variant={filter === 'pending' ? 'filled' : 'light'} onClick={() => setFilter('pending')}>
          Pending
        </Button>
        <Button size="xs" variant={!filter ? 'filled' : 'light'} onClick={() => setFilter(null)}>
          Все
        </Button>
      </Group>
      <Table withTableBorder>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>ID</Table.Th>
            <Table.Th>Event</Table.Th>
            <Table.Th>Status</Table.Th>
            <Table.Th>Attempt</Table.Th>
            <Table.Th>Error</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {deliveries.map((d) => (
            <Table.Tr key={d.id}>
              <Table.Td>{d.id}</Table.Td>
              <Table.Td>{d.event}</Table.Td>
              <Table.Td>
                <Badge color={d.status === 'delivered' ? 'teal' : d.status === 'dlq' ? 'red' : 'orange'}>
                  {d.status}
                </Badge>
              </Table.Td>
              <Table.Td>{d.attempt}</Table.Td>
              <Table.Td>
                <Text size="xs" lineClamp={1}>
                  {d.error || '—'}
                </Text>
              </Table.Td>
              <Table.Td>
                {d.status !== 'delivered' && (
                  <Button size="xs" onClick={() => retry(d.id)}>
                    Retry
                  </Button>
                )}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </SellerShell>
  );
}
