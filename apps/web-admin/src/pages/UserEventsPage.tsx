import { Button, Center, Group, Loader, Select, Stack, Text, TextInput } from '@mantine/core';
import { IconRefresh } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { useCallback, useEffect, useState } from 'react';
import { PageHeader, ShellTable } from '../components/Panel';
import { api, getApiError } from '../services/api';

type EventRow = {
  event_id: string;
  user_id?: number | null;
  company_id?: number | null;
  member_role?: string | null;
  event_type: string;
  payload?: Record<string, unknown> | null;
  created_at?: string | null;
};

export default function UserEventsPage() {
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<EventRow[]>([]);
  const [total, setTotal] = useState(0);
  const [types, setTypes] = useState<string[]>([]);
  const [userId, setUserId] = useState('');
  const [companyId, setCompanyId] = useState('');
  const [eventType, setEventType] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const limit = 100;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { limit, offset };
      if (userId.trim()) params.user_id = Number(userId);
      if (companyId.trim()) params.company_id = Number(companyId);
      if (eventType) params.event_type = eventType;
      const { data } = await api.get<{ items: EventRow[]; total: number }>('/admin/user-events', { params });
      setItems(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setLoading(false);
    }
  }, [companyId, eventType, offset, userId]);

  useEffect(() => {
    void api.get<{ items: string[] }>('/admin/user-events/taxonomy').then((r) => {
      setTypes(r.data.items ?? []);
    });
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="vz-page">
      <PageHeader
        title="User events"
        description="§12.1 — события пользователей из PostgreSQL"
        action={
          <Button leftSection={<IconRefresh size={16} />} variant="light" onClick={() => void load()}>
            Обновить
          </Button>
        }
      />

      <Stack className="vz-surface" mb="md">
        <Group grow align="flex-end">
          <TextInput label="User ID" value={userId} onChange={(e) => setUserId(e.currentTarget.value)} />
          <TextInput label="Company ID" value={companyId} onChange={(e) => setCompanyId(e.currentTarget.value)} />
          <Select
            label="Event type"
            clearable
            searchable
            data={types.map((t) => ({ value: t, label: t }))}
            value={eventType}
            onChange={setEventType}
          />
          <Button
            onClick={() => {
              setOffset(0);
              void load();
            }}
          >
            Фильтр
          </Button>
        </Group>
        <Text size="sm" c="dimmed">
          Всего: {total}
        </Text>
      </Stack>

      {loading && !items.length ? (
        <Center py="xl">
          <Loader color="brand" />
        </Center>
      ) : (
        <ShellTable
          headers={['Время', 'User', 'Company', 'Тип', 'Payload']}
          rows={items.map((r) => [
            r.created_at ? new Date(r.created_at).toLocaleString('ru-RU') : '—',
            String(r.user_id ?? '—'),
            String(r.company_id ?? '—'),
            r.event_type,
            <Text key={r.event_id} size="xs" lineClamp={2} maw={280}>
              {r.payload ? JSON.stringify(r.payload) : '—'}
            </Text>,
          ])}
        />
      )}

      <Group mt="md" justify="center">
        <Button variant="light" disabled={offset <= 0} onClick={() => setOffset((o) => Math.max(0, o - limit))}>
          Назад
        </Button>
        <Text size="sm">
          {offset + 1}–{Math.min(offset + limit, total)} / {total}
        </Text>
        <Button variant="light" disabled={offset + limit >= total} onClick={() => setOffset((o) => o + limit)}>
          Вперёд
        </Button>
      </Group>
    </div>
  );
}
