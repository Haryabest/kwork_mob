'use client';

import { Button, Group, Select, Stack, Table, Text, TextInput, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useCallback, useEffect, useState } from 'react';
import { SellerShell } from '../../../components/SellerShell';
import { api, apiMessage } from '../../../services/api';

type Row = {
  id: number;
  user_id?: number;
  action: string;
  details?: Record<string, unknown>;
  ip_address?: string | null;
  created_at?: string;
};

const ACTION_FILTER = [
  { value: '', label: 'Все действия' },
  { value: 'oauth_', label: 'OAuth (oauth_*)' },
  { value: 'oauth_login', label: 'oauth_login' },
  { value: 'oauth_link', label: 'oauth_link' },
  { value: 'oauth_unlink', label: 'oauth_unlink' },
];

function buildParams(actionFilter: string | null, dateFrom: string, dateTo: string, ip: string) {
  const params: Record<string, string> = {};
  const f = actionFilter ?? '';
  if (f === 'oauth_login' || f === 'oauth_link' || f === 'oauth_unlink') {
    params.action = f;
  } else if (f === 'oauth_') {
    params.action_prefix = 'oauth_';
  }
  if (dateFrom) params.date_from = `${dateFrom}T00:00:00Z`;
  if (dateTo) params.date_to = `${dateTo}T23:59:59Z`;
  if (ip.trim()) params.ip = ip.trim();
  return params;
}

export default function AuditPage() {
  const [items, setItems] = useState<Row[]>([]);
  const [actionFilter, setActionFilter] = useState<string | null>('oauth_');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [ip, setIp] = useState('');

  const load = useCallback(async () => {
    const params = buildParams(actionFilter, dateFrom, dateTo, ip);
    const { data } = await api.get<{ items: Row[] }>('/company/audit', { params });
    setItems(data.items ?? []);
  }, [actionFilter, dateFrom, dateTo, ip]);

  useEffect(() => {
    load().catch((e) => notifications.show({ color: 'red', message: apiMessage(e) }));
  }, [load]);

  async function exportCsv() {
    try {
      const params = buildParams(actionFilter, dateFrom, dateTo, ip);
      const { data } = await api.get('/company/audit/export', { params, responseType: 'blob' });
      const url = URL.createObjectURL(data);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'audit.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }

  return (
    <SellerShell>
      <Group justify="space-between" mb="lg" align="flex-end" wrap="wrap">
        <div>
          <Title order={2}>Аудит</Title>
          <Text c="dimmed" size="sm">
            Действия сотрудников компании
          </Text>
        </div>
        <Group align="flex-end" wrap="wrap">
          <TextInput type="date" label="С" value={dateFrom} onChange={(e) => setDateFrom(e.currentTarget.value)} />
          <TextInput type="date" label="По" value={dateTo} onChange={(e) => setDateTo(e.currentTarget.value)} />
          <TextInput label="IP" placeholder="192.168." value={ip} onChange={(e) => setIp(e.currentTarget.value)} w={140} />
          <Select label="Действие" data={ACTION_FILTER} value={actionFilter} onChange={setActionFilter} w={200} />
          <Button variant="light" onClick={() => void load()}>
            Применить
          </Button>
          <Button variant="light" onClick={() => void exportCsv()}>
            Export CSV
          </Button>
        </Group>
      </Group>
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>ID</Table.Th>
            <Table.Th>User</Table.Th>
            <Table.Th>Action</Table.Th>
            <Table.Th>IP</Table.Th>
            <Table.Th>Details</Table.Th>
            <Table.Th>When</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {items.length === 0 ? (
            <Table.Tr>
              <Table.Td colSpan={6}>
                <Text ta="center" c="dimmed" py="xl">
                  Пусто
                </Text>
              </Table.Td>
            </Table.Tr>
          ) : (
            items.map((r) => (
              <Table.Tr key={r.id}>
                <Table.Td>{r.id}</Table.Td>
                <Table.Td>{r.user_id ?? '—'}</Table.Td>
                <Table.Td>{r.action}</Table.Td>
                <Table.Td>{r.ip_address ?? '—'}</Table.Td>
                <Table.Td>
                  {r.details?.provider
                    ? `${String(r.details.provider)}${r.details.platform ? ` (${String(r.details.platform)})` : ''}`
                    : '—'}
                </Table.Td>
                <Table.Td>{r.created_at ?? '—'}</Table.Td>
              </Table.Tr>
            ))
          )}
        </Table.Tbody>
      </Table>
    </SellerShell>
  );
}
