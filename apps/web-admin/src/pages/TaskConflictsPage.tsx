import { useCallback, useEffect, useState } from 'react';
import { Button, Table, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconRefresh } from '@tabler/icons-react';
import { api, getApiError } from '../services/api';

type Row = {
  id: number;
  task_id: string;
  worker_id?: string | null;
  reason: string;
  details?: Record<string, unknown>;
  created_at?: string | null;
};

/** Журнал Redlock / task_conflicts §4.8.5 / §12.4.1 */
export default function TaskConflictsPage() {
  const [items, setItems] = useState<Row[]>([]);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get<{ items: Row[] }>('/admin/task-conflicts', {
        params: { limit: 200 },
      });
      setItems(data.items ?? []);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="vz-page">
      <div className="vz-page-header">
        <div>
          <Title order={2}>Task conflicts</Title>
          <Text c="#6d6c77" size="sm" mt={6}>
            Redlock / duplicate completion · {items.length} записей
          </Text>
        </div>
        <Button leftSection={<IconRefresh size={16} />} variant="light" onClick={() => void load()}>
          Обновить
        </Button>
      </div>
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>ID</Table.Th>
            <Table.Th>Task</Table.Th>
            <Table.Th>Worker</Table.Th>
            <Table.Th>Reason</Table.Th>
            <Table.Th>Details</Table.Th>
            <Table.Th>Когда</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {items.length === 0 ? (
            <Table.Tr>
              <Table.Td colSpan={6}>
                <Text ta="center" c="dimmed" py="xl">
                  Конфликтов нет
                </Text>
              </Table.Td>
            </Table.Tr>
          ) : (
            items.map((r) => (
              <Table.Tr key={r.id}>
                <Table.Td>{r.id}</Table.Td>
                <Table.Td>
                  <code>{r.task_id?.slice(0, 12)}…</code>
                </Table.Td>
                <Table.Td>{r.worker_id ?? '—'}</Table.Td>
                <Table.Td>{r.reason}</Table.Td>
                <Table.Td>
                  <Text size="xs" maw={280} style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {r.details ? JSON.stringify(r.details) : '—'}
                  </Text>
                </Table.Td>
                <Table.Td>{r.created_at ?? '—'}</Table.Td>
              </Table.Tr>
            ))
          )}
        </Table.Tbody>
      </Table>
    </div>
  );
}
