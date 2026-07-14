import { useCallback, useEffect, useState } from 'react';
import { Button, Group, Table, Text, TextInput, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconDownload, IconRefresh } from '@tabler/icons-react';
import { api, getApiError } from '../services/api';

type Row = {
  id: number;
  user_id: number;
  company_id?: number | null;
  model_uuid: string;
  action?: string;
  file_format?: string | null;
  ip_address?: string | null;
  timestamp?: string | null;
};

/** Глобальный access_log §10.7.2 */
export default function AccessLogPage() {
  const [items, setItems] = useState<Row[]>([]);
  const [total, setTotal] = useState(0);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [companyId, setCompanyId] = useState('');
  const [modelUuid, setModelUuid] = useState('');

  const load = useCallback(async () => {
    try {
      const { data } = await api.get<{ items: Row[]; total: number }>('/admin/access-log', {
        params: {
          date_from: dateFrom ? `${dateFrom}T00:00:00Z` : undefined,
          date_to: dateTo ? `${dateTo}T23:59:59Z` : undefined,
          company_id: companyId || undefined,
          model_uuid: modelUuid || undefined,
        },
      });
      setItems(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }, [dateFrom, dateTo, companyId, modelUuid]);

  useEffect(() => {
    void load();
  }, [load]);

  async function exportCsv() {
    try {
      const { data } = await api.get<Blob>('/admin/access-log/export', {
        responseType: 'blob',
        params: {
          date_from: dateFrom ? `${dateFrom}T00:00:00Z` : undefined,
          date_to: dateTo ? `${dateTo}T23:59:59Z` : undefined,
          company_id: companyId || undefined,
        },
      });
      const url = URL.createObjectURL(data);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'access-log.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  return (
    <div className="vz-page">
      <div className="vz-page-header">
        <div>
          <Title order={2}>Access log</Title>
          <Text c="#6d6c77" size="sm" mt={6}>
            Аудит скачиваний моделей §10.7.2 · всего {total}
          </Text>
        </div>
        <Group>
          <Button leftSection={<IconRefresh size={16} />} variant="light" onClick={() => void load()}>
            Обновить
          </Button>
          <Button leftSection={<IconDownload size={16} />} variant="light" onClick={() => void exportCsv()}>
            CSV
          </Button>
          <Button
            variant="light"
            onClick={async () => {
              try {
                const { data } = await api.post<{ prefix?: string; audit_rows?: number; access_rows?: number }>(
                  '/admin/audit-export/run',
                );
                notifications.show({
                  color: 'teal',
                  message: `Экспорт ${data.prefix}: audit=${data.audit_rows} access=${data.access_rows} → MinIO audit-logs`,
                });
              } catch (e) {
                notifications.show({ color: 'red', message: getApiError(e) });
              }
            }}
          >
            Monthly → MinIO
          </Button>
        </Group>
      </div>

      <div className="vz-surface" style={{ marginBottom: '1rem' }}>
        <Group align="flex-end" wrap="wrap">
          <TextInput type="date" label="С" value={dateFrom} onChange={(e) => setDateFrom(e.currentTarget.value)} />
          <TextInput type="date" label="По" value={dateTo} onChange={(e) => setDateTo(e.currentTarget.value)} />
          <TextInput label="Company ID" value={companyId} onChange={(e) => setCompanyId(e.currentTarget.value)} maw={120} />
          <TextInput label="Model UUID" value={modelUuid} onChange={(e) => setModelUuid(e.currentTarget.value)} maw={280} />
          <Button onClick={() => void load()}>Фильтр</Button>
        </Group>
      </div>

      <div className="vz-surface">
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Время</Table.Th>
              <Table.Th>User</Table.Th>
              <Table.Th>Company</Table.Th>
              <Table.Th>Model</Table.Th>
              <Table.Th>Format</Table.Th>
              <Table.Th>IP</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {items.map((r) => (
              <Table.Tr key={r.id}>
                <Table.Td>{r.timestamp ? new Date(r.timestamp).toLocaleString('ru-RU') : '—'}</Table.Td>
                <Table.Td>{r.user_id}</Table.Td>
                <Table.Td>{r.company_id ?? '—'}</Table.Td>
                <Table.Td>{r.model_uuid.slice(0, 8)}…</Table.Td>
                <Table.Td>{r.file_format ?? '—'}</Table.Td>
                <Table.Td>{r.ip_address ?? '—'}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </div>
    </div>
  );
}
