'use client';

import {
  Button,
  Group,
  Modal,
  MultiSelect,
  NumberInput,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';
import { SellerShell } from '../../../components/SellerShell';
import { api, apiMessage } from '../../../services/api';

type KeyRow = {
  id: number;
  name: string;
  key_prefix: string;
  scopes: string[];
  rate_limit_per_min: number;
  daily_limit?: number;
  is_active: boolean;
  created_at?: string;
};

const SCOPE_OPTIONS = [
  { value: 'order:create', label: 'order:create' },
  { value: 'order:read', label: 'order:read' },
  { value: 'balance:read', label: 'balance:read' },
  { value: 'member:list', label: 'member:list' },
  { value: 'shoot_link:create', label: 'shoot_link:create' },
];

export default function ApiKeysPage() {
  const [opened, { open, close }] = useDisclosure(false);
  const [items, setItems] = useState<KeyRow[]>([]);
  const [name, setName] = useState('');
  const [scopes, setScopes] = useState<string[]>(['order:create', 'order:read']);
  const [rate, setRate] = useState<number | string>(1000);
  const [daily, setDaily] = useState<number | string>(100000);
  const [plain, setPlain] = useState<string | null>(null);

  async function load() {
    const { data } = await api.get<{ items: KeyRow[] }>('/company/api_keys');
    setItems(data.items ?? []);
  }

  useEffect(() => {
    load().catch((e) => notifications.show({ color: 'red', message: apiMessage(e) }));
  }, []);

  async function create() {
    try {
      const { data } = await api.post<{ key: string }>('/company/api_keys', {
        name,
        scopes,
        rate_limit_per_min: Number(rate) || 1000,
        daily_limit: Number(daily) || 100000,
      });
      setPlain(data.key);
      notifications.show({ color: 'teal', message: 'Скопируйте ключ — он больше не покажется' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }

  async function revoke(id: number) {
    try {
      await api.delete(`/company/api_keys/${id}`);
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }

  return (
    <SellerShell>
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>API-ключи</Title>
          <Text c="dimmed" size="sm">
            Owner · scopes · rate limit
          </Text>
        </div>
        <Button
          onClick={() => {
            setPlain(null);
            open();
          }}
        >
          Создать ключ
        </Button>
      </Group>
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Название</Table.Th>
            <Table.Th>Префикс</Table.Th>
            <Table.Th>Scopes</Table.Th>
            <Table.Th>Лимит/мин</Table.Th>
            <Table.Th>Лимит/сутки</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {items.length === 0 ? (
            <Table.Tr>
              <Table.Td colSpan={6}>
                <Text ta="center" c="dimmed" py="xl">
                  API-ключей пока нет
                </Text>
              </Table.Td>
            </Table.Tr>
          ) : (
            items.map((k) => (
              <Table.Tr key={k.id} opacity={k.is_active ? 1 : 0.5}>
                <Table.Td>{k.name}</Table.Td>
                <Table.Td>
                  <code>{k.key_prefix}…</code>
                </Table.Td>
                <Table.Td>{(k.scopes || []).join(', ')}</Table.Td>
                <Table.Td>{k.rate_limit_per_min}</Table.Td>
                <Table.Td>{k.daily_limit ?? '—'}</Table.Td>
                <Table.Td>
                  {k.is_active && (
                    <Button size="xs" color="red" variant="light" onClick={() => revoke(k.id)}>
                      Отозвать
                    </Button>
                  )}
                </Table.Td>
              </Table.Tr>
            ))
          )}
        </Table.Tbody>
      </Table>
      <Modal opened={opened} onClose={close} title="Создать API-ключ">
        <Stack>
          <TextInput label="Название" value={name} onChange={(e) => setName(e.currentTarget.value)} />
          <MultiSelect label="Scopes" data={SCOPE_OPTIONS} value={scopes} onChange={setScopes} />
          <NumberInput label="Rate limit / мин" value={rate} onChange={setRate} min={10} max={10000} />
          <NumberInput
            label="Daily limit (запросов/сутки)"
            value={daily}
            onChange={setDaily}
            min={100}
            max={10000000}
          />
          {plain && (
            <Text size="sm" c="teal">
              Ключ: <code>{plain}</code>
            </Text>
          )}
          <Button onClick={create} disabled={!name || scopes.length === 0}>
            Создать
          </Button>
        </Stack>
      </Modal>
    </SellerShell>
  );
}
