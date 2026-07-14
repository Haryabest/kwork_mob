import { useCallback, useEffect, useState } from 'react';
import {
  Badge,
  Button,
  Group,
  PasswordInput,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconRefresh } from '@tabler/icons-react';
import { api, getApiError } from '../services/api';

type Cred = {
  id: number;
  company_id?: number | null;
  marketplace: string;
  api_key_masked?: string;
  client_id?: string | null;
  enabled: boolean;
  updated_at?: string | null;
};

type LogRow = {
  id: number;
  model_uuid?: string;
  marketplace?: string;
  status?: string;
  attempts?: number;
  error?: string | null;
  created_at?: string | null;
};

/** Admin: WB/Ozon API credentials + upload logs (§7.6 / §14.6). */
export default function MarketplacePage() {
  const [status, setStatus] = useState<{ upload_enabled?: boolean; max_retries?: number }>({});
  const [creds, setCreds] = useState<Cred[]>([]);
  const [logs, setLogs] = useState<LogRow[]>([]);
  const [marketplace, setMarketplace] = useState<string | null>('wb');
  const [apiKey, setApiKey] = useState('');
  const [clientId, setClientId] = useState('');
  const [companyId, setCompanyId] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [s, c, l] = await Promise.all([
        api.get('/admin/marketplace/status'),
        api.get<{ items: Cred[] }>('/admin/marketplace/credentials'),
        api.get<{ items: LogRow[] }>('/admin/marketplace/upload-logs'),
      ]);
      setStatus(s.data);
      setCreds(c.data.items ?? []);
      setLogs(l.data.items ?? []);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function saveCred() {
    if (!marketplace || apiKey.length < 8) {
      return notifications.show({ color: 'red', message: 'API key ≥ 8 символов' });
    }
    setBusy(true);
    try {
      await api.put('/admin/marketplace/credentials', {
        marketplace,
        api_key: apiKey,
        client_id: clientId || null,
        company_id: companyId ? Number(companyId) : null,
        enabled: true,
      });
      setApiKey('');
      notifications.show({ color: 'teal', message: 'Credentials сохранены' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="vz-page">
      <div className="vz-page-header">
        <div>
          <Title order={2}>Marketplace API</Title>
          <Text c="#6d6c77" size="sm" mt={6}>
            WB/Ozon credentials · upload enabled:{' '}
            <Badge color={status.upload_enabled ? 'teal' : 'gray'} variant="light">
              {status.upload_enabled ? 'on' : 'off'}
            </Badge>
          </Text>
        </div>
        <Button leftSection={<IconRefresh size={16} />} variant="light" onClick={() => void load()}>
          Обновить
        </Button>
      </div>

      <div className="vz-grid vz-grid-2-lg">
        <div className="vz-surface">
          <Text fw={600} mb="md">
            Добавить / обновить ключ
          </Text>
          <Stack>
            <Select
              label="Маркетплейс"
              data={[
                { value: 'wb', label: 'Wildberries' },
                { value: 'ozon', label: 'Ozon' },
              ]}
              value={marketplace}
              onChange={setMarketplace}
            />
            <PasswordInput label="API key" value={apiKey} onChange={(e) => setApiKey(e.currentTarget.value)} />
            <TextInput
              label="Client ID (Ozon)"
              value={clientId}
              onChange={(e) => setClientId(e.currentTarget.value)}
            />
            <TextInput
              label="Company ID (пусто = глобальный)"
              value={companyId}
              onChange={(e) => setCompanyId(e.currentTarget.value)}
            />
            <Button loading={busy} onClick={() => void saveCred()}>
              Сохранить
            </Button>
          </Stack>
        </div>

        <div className="vz-surface">
          <Text fw={600} mb="md">
            Credentials
          </Text>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>MP</Table.Th>
                <Table.Th>Company</Table.Th>
                <Table.Th>Key</Table.Th>
                <Table.Th>On</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {creds.map((c) => (
                <Table.Tr key={c.id}>
                  <Table.Td>{c.marketplace}</Table.Td>
                  <Table.Td>{c.company_id ?? '—'}</Table.Td>
                  <Table.Td>{c.api_key_masked}</Table.Td>
                  <Table.Td>
                    <Switch
                      checked={c.enabled}
                      onChange={async (e) => {
                        try {
                          await api.patch(`/admin/marketplace/credentials/${c.id}`, {
                            enabled: e.currentTarget.checked,
                          });
                          await load();
                        } catch (err) {
                          notifications.show({ color: 'red', message: getApiError(err) });
                        }
                      }}
                    />
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </div>
      </div>

      <div className="vz-surface" style={{ marginTop: '1.5rem' }}>
        <Text fw={600} mb="md">
          Upload logs
        </Text>
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>Model</Table.Th>
              <Table.Th>MP</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>When</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {logs.map((l) => (
              <Table.Tr key={l.id}>
                <Table.Td>{l.id}</Table.Td>
                <Table.Td>{l.model_uuid?.slice(0, 8)}</Table.Td>
                <Table.Td>{l.marketplace}</Table.Td>
                <Table.Td>{l.status}</Table.Td>
                <Table.Td>{l.created_at ? new Date(l.created_at).toLocaleString('ru-RU') : '—'}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </div>
    </div>
  );
}
