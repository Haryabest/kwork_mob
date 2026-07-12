'use client';

import { Button, Group, Select, Stack, Table, Text, TextInput, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';
import { SellerShell } from '../../../components/SellerShell';
import { api, apiMessage } from '../../../services/api';

type Member = {
  user_id: number;
  email?: string;
  role: string;
  max_concurrent_orders?: number;
  monthly_spending_limit?: number;
};

export default function RolesPage() {
  const [items, setItems] = useState<Member[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>('photographer');

  async function load() {
    const { data } = await api.get<{ items: Member[] }>('/company/members');
    setItems(data.items ?? []);
  }

  useEffect(() => {
    load().catch((e) => notifications.show({ color: 'red', message: apiMessage(e) }));
  }, []);

  async function saveRole() {
    if (!selected || !role) return;
    try {
      await api.patch(`/company/members/${selected}/role`, { role });
      notifications.show({ color: 'teal', message: 'Роль обновлена' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }

  async function remove(uid: number) {
    try {
      await api.delete(`/company/members/${uid}`);
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }

  return (
    <SellerShell>
      <Title order={2} mb="md">
        Роли и участники
      </Title>
      <Table mb="lg">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Email</Table.Th>
            <Table.Th>Роль</Table.Th>
            <Table.Th>Лимит заказов</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {items.map((m) => (
            <Table.Tr key={m.user_id}>
              <Table.Td>{m.email}</Table.Td>
              <Table.Td>{m.role}</Table.Td>
              <Table.Td>{m.max_concurrent_orders ?? '—'}</Table.Td>
              <Table.Td>
                <Button size="xs" color="red" variant="light" onClick={() => remove(m.user_id)}>
                  Удалить
                </Button>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
      <Stack maw={420}>
        <Select
          label="Участник"
          value={selected}
          onChange={setSelected}
          data={items.map((m) => ({ value: String(m.user_id), label: m.email || String(m.user_id) }))}
        />
        <Select
          label="Новая роль"
          value={role}
          onChange={setRole}
          data={[
            { value: 'manager', label: 'Manager' },
            { value: 'photographer', label: 'Photographer' },
            { value: 'viewer', label: 'Viewer' },
          ]}
        />
        <Button onClick={saveRole} w="fit-content">
          Сохранить роль
        </Button>
      </Stack>
    </SellerShell>
  );
}
