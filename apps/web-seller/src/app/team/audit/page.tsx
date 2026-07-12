'use client';

import { Button, Group, Stack, Table, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';
import { SellerShell } from '../../../components/SellerShell';
import { api, apiMessage } from '../../../services/api';

type Row = { id: number; user_id?: number; action: string; details?: unknown; created_at?: string };

export default function AuditPage() {
  const [items, setItems] = useState<Row[]>([]);

  async function load() {
    const { data } = await api.get<{ items: Row[] }>('/company/audit');
    setItems(data.items ?? []);
  }

  useEffect(() => {
    load().catch((e) => notifications.show({ color: 'red', message: apiMessage(e) }));
  }, []);

  async function exportCsv() {
    try {
      const { data } = await api.get('/company/audit/export', { responseType: 'blob' });
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
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>Аудит</Title>
          <Text c="dimmed" size="sm">
            Действия сотрудников компании
          </Text>
        </div>
        <Button variant="light" onClick={exportCsv}>
          Export CSV
        </Button>
      </Group>
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>ID</Table.Th>
            <Table.Th>User</Table.Th>
            <Table.Th>Action</Table.Th>
            <Table.Th>When</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {items.length === 0 ? (
            <Table.Tr>
              <Table.Td colSpan={4}>
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
                <Table.Td>{r.created_at ?? '—'}</Table.Td>
              </Table.Tr>
            ))
          )}
        </Table.Tbody>
      </Table>
    </SellerShell>
  );
}
