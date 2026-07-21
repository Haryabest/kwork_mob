import { useCallback, useEffect, useState } from 'react';
import { Button, Group, Select, Table, Text, TextInput, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconDownload, IconRefresh, IconSettings } from '@tabler/icons-react';
import { Link } from 'react-router-dom';
import { api, getApiError } from '../services/api';

type Row = {
  id: number;
  channel: string;
  event_type: string;
  text?: string | null;
  company_id?: number | string | null;
  worker_id?: string | null;
  ok: boolean;
  error?: string | null;
  created_at?: string | null;
};

/** История alert_log §12.4.3 */
export default function AlertLogPage() {
  const [items, setItems] = useState<Row[]>([]);
  const [total, setTotal] = useState(0);
  const [eventType, setEventType] = useState('');
  const [channel, setChannel] = useState<string | null>(null);
  const [okFilter, setOkFilter] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const load = useCallback(async () => {
    try {
      const { data } = await api.get<{ items: Row[]; total: number }>('/admin/alerts/log', {
        params: {
          event_type: eventType || undefined,
          channel: channel || undefined,
          ok: okFilter === '1' ? true : okFilter === '0' ? false : undefined,
          date_from: dateFrom ? `${dateFrom}T00:00:00Z` : undefined,
          date_to: dateTo ? `${dateTo}T23:59:59Z` : undefined,
          limit: 200,
        },
      });
      setItems(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }, [eventType, channel, okFilter, dateFrom, dateTo]);

  useEffect(() => {
    void load();
  }, [load]);

  async function exportCsv() {
    try {
      const { data } = await api.get<Blob>('/admin/alerts/log/export', {
        responseType: 'blob',
        params: {
          event_type: eventType || undefined,
          channel: channel || undefined,
          ok: okFilter === '1' ? true : okFilter === '0' ? false : undefined,
          date_from: dateFrom ? `${dateFrom}T00:00:00Z` : undefined,
          date_to: dateTo ? `${dateTo}T23:59:59Z` : undefined,
        },
      });
      const url = URL.createObjectURL(data);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'alert-log.csv';
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
          <Title order={2}>Alert log</Title>
          <Text c="#6d6c77" size="sm" mt={6}>
            История алертов §12.4.3 · {total} записей
          </Text>
        </div>
        <Group>
          <Button component={Link} to="/settings#alert-thresholds" variant="light" leftSection={<IconSettings size={16} />}>
            Пороги алертов
          </Button>
          <Button leftSection={<IconRefresh size={16} />} variant="light" onClick={() => void load()}>
            Обновить
          </Button>
          <Button leftSection={<IconDownload size={16} />} variant="light" onClick={() => void exportCsv()}>
            CSV
          </Button>
        </Group>
      </div>

      <Group mb="md" align="flex-end">
        <TextInput
          label="Тип события"
          placeholder="queue_length"
          value={eventType}
          onChange={(e) => setEventType(e.currentTarget.value)}
          w={180}
        />
        <Select
          label="Канал"
          clearable
          data={[
            { value: 'telegram', label: 'telegram' },
            { value: 'email', label: 'email' },
          ]}
          value={channel}
          onChange={setChannel}
          w={140}
        />
        <Select
          label="Доставка"
          clearable
          data={[
            { value: '1', label: 'ok' },
            { value: '0', label: 'fail' },
          ]}
          value={okFilter}
          onChange={setOkFilter}
          w={120}
        />
        <TextInput type="date" label="С" value={dateFrom} onChange={(e) => setDateFrom(e.currentTarget.value)} />
        <TextInput type="date" label="По" value={dateTo} onChange={(e) => setDateTo(e.currentTarget.value)} />
      </Group>

      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Когда</Table.Th>
            <Table.Th>Тип</Table.Th>
            <Table.Th>Канал</Table.Th>
            <Table.Th>OK</Table.Th>
            <Table.Th>Company</Table.Th>
            <Table.Th>Worker</Table.Th>
            <Table.Th>Текст / ошибка</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {items.length === 0 ? (
            <Table.Tr>
              <Table.Td colSpan={7}>
                <Text ta="center" c="dimmed" py="xl">
                  Нет записей
                </Text>
              </Table.Td>
            </Table.Tr>
          ) : (
            items.map((r) => (
              <Table.Tr key={r.id}>
                <Table.Td>{r.created_at ?? '—'}</Table.Td>
                <Table.Td>
                  <code>{r.event_type}</code>
                </Table.Td>
                <Table.Td>{r.channel}</Table.Td>
                <Table.Td>{r.ok ? '✓' : '✗'}</Table.Td>
                <Table.Td>{r.company_id ?? '—'}</Table.Td>
                <Table.Td>{r.worker_id ?? '—'}</Table.Td>
                <Table.Td>
                  <Text size="xs" maw={360} style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {r.error || r.text || '—'}
                  </Text>
                </Table.Td>
              </Table.Tr>
            ))
          )}
        </Table.Tbody>
      </Table>
    </div>
  );
}
