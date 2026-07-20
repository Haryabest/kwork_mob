'use client';

import {
  Badge,
  Button,
  Group,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useCallback, useEffect, useState } from 'react';
import { SellerShell } from '../../../components/SellerShell';
import { PageHeader, Surface } from '../../../components/ui';
import { api, apiMessage } from '../../../services/api';

type Cred = {
  id: number;
  marketplace: string;
  api_key_masked: string;
  client_id?: string | null;
  enabled: boolean;
  updated_at?: string | null;
};

/** Owner: WB/Ozon API-ключи компании §7.6 / §14.6 */
export default function TeamMarketplacePage() {
  const [items, setItems] = useState<Cred[]>([]);
  const [uploadEnabled, setUploadEnabled] = useState(false);
  const [marketplace, setMarketplace] = useState<string | null>('wb');
  const [apiKey, setApiKey] = useState('');
  const [clientId, setClientId] = useState('');
  const [enabled, setEnabled] = useState(true);
  const [busy, setBusy] = useState(false);
  const [mpStatus, setMpStatus] = useState<{ credentials?: { wb?: boolean; ozon?: boolean } } | null>(null);

  const load = useCallback(async () => {
    const [creds, status] = await Promise.all([
      api.get<{ items: Cred[]; upload_enabled: boolean }>('/company/marketplace/credentials'),
      api.get<{ credentials?: { wb?: boolean; ozon?: boolean }; upload_enabled?: boolean }>(
        '/company/marketplace/status',
      ),
    ]);
    setItems(creds.data.items ?? []);
    setUploadEnabled(Boolean(creds.data.upload_enabled));
    setMpStatus(status.data);
  }, []);

  useEffect(() => {
    load().catch((e) => notifications.show({ color: 'red', message: apiMessage(e) }));
  }, [load]);

  async function save() {
    if (!marketplace || apiKey.length < 8) {
      notifications.show({ color: 'orange', message: 'Выберите маркетплейс и API-ключ (≥8 символов)' });
      return;
    }
    setBusy(true);
    try {
      await api.put('/company/marketplace/credentials', {
        marketplace,
        api_key: apiKey,
        client_id: marketplace === 'ozon' ? clientId || null : null,
        enabled,
      });
      setApiKey('');
      notifications.show({ color: 'teal', message: 'Ключ сохранён' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <SellerShell>
      <PageHeader
        title="Marketplace API"
        description="WB/Ozon ключи компании для API-публикации 3D-моделей"
      />
      <Surface mb="md">
        <Group mb="sm">
          <Text fw={600}>Статус сервиса</Text>
          <Badge color={uploadEnabled ? 'teal' : 'gray'}>
            API upload: {uploadEnabled ? 'включён' : 'выключен (admin)'}
          </Badge>
          <Badge color={mpStatus?.credentials?.wb ? 'teal' : 'gray'}>
            WB: {mpStatus?.credentials?.wb ? 'ключ есть' : 'нет ключа'}
          </Badge>
          <Badge color={mpStatus?.credentials?.ozon ? 'teal' : 'gray'}>
            Ozon: {mpStatus?.credentials?.ozon ? 'ключ есть' : 'нет ключа'}
          </Badge>
        </Group>
        <Text size="sm" c="dimmed">
          После настройки ключей используйте «API upload» на карточке модели. Глобальные ключи владельца
          сервиса — fallback, если ключ компании не задан.
        </Text>
      </Surface>

      <Surface mb="md">
        <Title order={4} mb="md">
          Добавить / обновить ключ
        </Title>
        <Stack maw={480}>
          <Select
            label="Маркетплейс"
            data={[
              { value: 'wb', label: 'Wildberries' },
              { value: 'ozon', label: 'Ozon' },
            ]}
            value={marketplace}
            onChange={setMarketplace}
          />
          <TextInput
            label="API-ключ"
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.currentTarget.value)}
            placeholder="Минимум 8 символов"
          />
          {marketplace === 'ozon' && (
            <TextInput
              label="Client-Id (Ozon)"
              value={clientId}
              onChange={(e) => setClientId(e.currentTarget.value)}
            />
          )}
          <Switch label="Активен" checked={enabled} onChange={(e) => setEnabled(e.currentTarget.checked)} />
          <Button loading={busy} onClick={() => void save()}>
            Сохранить
          </Button>
        </Stack>
      </Surface>

      <Surface>
        <Title order={4} mb="md">
          Ключи компании
        </Title>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>MP</Table.Th>
              <Table.Th>Ключ</Table.Th>
              <Table.Th>Client-Id</Table.Th>
              <Table.Th>Статус</Table.Th>
              <Table.Th>Обновлён</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {items.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={5}>
                  <Text c="dimmed" size="sm">
                    Ключи не настроены
                  </Text>
                </Table.Td>
              </Table.Tr>
            ) : (
              items.map((c) => (
                <Table.Tr key={c.id}>
                  <Table.Td>{c.marketplace}</Table.Td>
                  <Table.Td>{c.api_key_masked}</Table.Td>
                  <Table.Td>{c.client_id || '—'}</Table.Td>
                  <Table.Td>
                    <Badge color={c.enabled ? 'teal' : 'gray'}>{c.enabled ? 'active' : 'off'}</Badge>
                  </Table.Td>
                  <Table.Td>{c.updated_at ? new Date(c.updated_at).toLocaleString('ru-RU') : '—'}</Table.Td>
                </Table.Tr>
              ))
            )}
          </Table.Tbody>
        </Table>
      </Surface>
    </SellerShell>
  );
}
