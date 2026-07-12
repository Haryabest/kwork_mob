import { Badge, Button, Center, Group, Loader, Stack, Text } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useCallback, useEffect, useState } from 'react';
import { MetricGrid, PageHeader, ShellTable, StateBadge } from '../components/Panel';
import { api, getApiError } from '../services/api';

type Report = {
  id: number;
  order_id: number;
  user_id: number;
  user_email?: string;
  user_status?: string;
  reason: string;
  refunded: boolean;
  verified: boolean;
  created_at?: string;
  hours_left?: number;
  overdue?: boolean;
  amount?: number;
  order_status?: string;
};

export default function ModerationPage() {
  const [items, setItems] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async () => {
    const { data } = await api.get<{ items: Report[] }>('/admin/nsfw/reports', {
      params: { verified: false },
    });
    setItems(data.items ?? []);
  }, []);

  useEffect(() => {
    load()
      .catch((e) => notifications.show({ color: 'red', message: getApiError(e) }))
      .finally(() => setLoading(false));
  }, [load]);

  async function verify(id: number, legal: boolean) {
    setBusyId(id);
    try {
      await api.post(`/admin/nsfw/${id}/verify`, { legal });
      notifications.show({
        color: legal ? 'teal' : 'orange',
        message: legal ? 'Ложное срабатывание — аккаунт разблокирован' : 'Нарушение подтверждено — бан',
      });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setBusyId(null);
    }
  }

  const overdue = items.filter((i) => i.overdue).length;
  const pending = items.length;

  if (loading) {
    return (
      <Center py="xl">
        <Loader color="brand" />
      </Center>
    );
  }

  return (
    <>
      <PageHeader
        title="Модерация NSFW"
        description="Ручная проверка в течение 24 часов (§10.8)"
        action={
          <Button variant="light" onClick={() => load().catch((e) => notifications.show({ color: 'red', message: getApiError(e) }))}>
            Обновить
          </Button>
        }
      />
      <MetricGrid
        items={[
          { label: 'Ожидают', value: String(pending), color: 'orange' },
          { label: 'Просрочено >24ч', value: String(overdue), color: overdue ? 'red' : 'teal' },
        ]}
      />
      <ShellTable
        headers={['ID', 'Заказ', 'Пользователь', 'Причина', 'SLA', 'Refund', 'Действия']}
        rows={
          items.length
            ? items.map((r) => [
                String(r.id),
                `#${r.order_id}${r.amount != null ? ` · ${r.amount}₽` : ''}`,
                <Stack key={`u-${r.id}`} gap={0}>
                  <Text size="sm">{r.user_email ?? r.user_id}</Text>
                  <Text size="xs" c="dimmed">
                    {r.user_status}
                  </Text>
                </Stack>,
                r.reason,
                r.overdue ? (
                  <Badge key={`s-${r.id}`} color="red">
                    просрочено
                  </Badge>
                ) : (
                  <Text key={`s-${r.id}`} size="sm">
                    {r.hours_left != null ? `${r.hours_left}ч` : '—'}
                  </Text>
                ),
                r.refunded ? <StateBadge key={`rf-${r.id}`} value="да" color="teal" /> : 'нет',
                <Group key={`a-${r.id}`} gap={6}>
                  <Button
                    size="xs"
                    color="teal"
                    loading={busyId === r.id}
                    onClick={() => void verify(r.id, true)}
                  >
                    Легально
                  </Button>
                  <Button
                    size="xs"
                    color="red"
                    variant="light"
                    loading={busyId === r.id}
                    onClick={() => void verify(r.id, false)}
                  >
                    Нарушение
                  </Button>
                </Group>,
              ])
            : [['—', 'Очередь пуста', '—', '—', '—', '—', '—']]
        }
      />
    </>
  );
}
