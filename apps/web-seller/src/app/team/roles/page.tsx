'use client';

import { Button, Checkbox, Group, Stack, Table, Text, TextInput, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';
import { SellerShell } from '../../../components/SellerShell';
import { api, apiMessage } from '../../../services/api';

type Role = {
  id: number;
  name: string;
  slug: string;
  permissions: Record<string, boolean>;
  is_system: boolean;
};

const DEFAULT_PERMS: Record<string, boolean> = {};

export default function RolesPage() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [keys, setKeys] = useState<string[]>([]);
  const [name, setName] = useState('');
  const [perms, setPerms] = useState<Record<string, boolean>>({ ...DEFAULT_PERMS });

  async function load() {
    const { data } = await api.get<{ items: Role[]; permission_keys: string[] }>('/company/roles');
    setRoles(data.items ?? []);
    setKeys(data.permission_keys ?? []);
    const init: Record<string, boolean> = {};
    for (const k of data.permission_keys ?? []) init[k] = false;
    setPerms(init);
  }

  useEffect(() => {
    load().catch((e) => notifications.show({ color: 'red', message: apiMessage(e) }));
  }, []);

  async function create() {
    try {
      await api.post('/company/roles', { name, permissions: perms });
      notifications.show({ color: 'teal', message: 'Роль создана' });
      setName('');
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }

  async function remove(id: number) {
    try {
      await api.delete(`/company/roles/${id}`);
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }

  return (
    <SellerShell>
      <Title order={2} mb="md">
        Управление ролями (§2.5.3)
      </Title>
      <Table mb="lg" withTableBorder>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Название</Table.Th>
            <Table.Th>Slug</Table.Th>
            <Table.Th>Тип</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {roles.map((r) => (
            <Table.Tr key={r.id}>
              <Table.Td>{r.name}</Table.Td>
              <Table.Td>{r.slug}</Table.Td>
              <Table.Td>{r.is_system ? 'системная' : 'кастом'}</Table.Td>
              <Table.Td>
                {!r.is_system && (
                  <Button size="xs" color="red" variant="light" onClick={() => remove(r.id)}>
                    Удалить
                  </Button>
                )}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <Title order={4} mb="sm">
        Создать кастомную роль
      </Title>
      <Stack maw={560}>
        <TextInput label="Название" value={name} onChange={(e) => setName(e.currentTarget.value)} />
        {keys.map((k) => (
          <Checkbox
            key={k}
            label={k}
            checked={!!perms[k]}
            onChange={(e) => setPerms({ ...perms, [k]: e.currentTarget.checked })}
          />
        ))}
        <Group>
          <Button onClick={create} disabled={name.length < 2}>
            Создать роль
          </Button>
        </Group>
      </Stack>
    </SellerShell>
  );
}
