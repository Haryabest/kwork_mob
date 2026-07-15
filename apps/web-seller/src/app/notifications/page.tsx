'use client';

import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Stack,
  Text,
  ThemeIcon,
} from '@mantine/core';
import {
  IconBell,
  IconBox,
  IconCheck,
  IconReceipt,
  IconShield,
  IconTrash,
  IconWallet,
} from '@tabler/icons-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { notifications } from '@mantine/notifications';
import { SellerShell } from '../../components/SellerShell';
import { EmptyState, PageHeader, Surface } from '../../components/ui';
import { api, apiMessage } from '../../services/api';

type InboxItem = {
  id: number;
  title: string;
  body?: string;
  type?: string;
  order_id?: number | null;
  model_uuid?: string | null;
  read?: boolean;
  created_at?: string | null;
};

function iconFor(type?: string) {
  switch (type) {
    case 'refund':
      return IconWallet;
    case 'nsfw_blocked':
      return IconShield;
    case 'generation_done':
      return IconBox;
    case 'generation_failed':
      return IconReceipt;
    default:
      return IconBell;
  }
}

function iconColor(type?: string) {
  if (type === 'refund') return 'teal';
  if (type === 'nsfw_blocked') return 'red';
  if (type === 'generation_done') return 'brand';
  return 'gray';
}

/** §19.16 / §20 — inbox уведомлений web-seller */
export default function NotificationsPage() {
  const router = useRouter();
  const [items, setItems] = useState<InboxItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [unread, setUnread] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<{ items: InboxItem[]; unread?: number }>('/user/notifications', {
        params: { limit: 50, offset: 0 },
      });
      setItems(data.items ?? []);
      setUnread(data.unread ?? 0);
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function openItem(item: InboxItem) {
    if (!item.read) {
      try {
        await api.post(`/user/notifications/${item.id}/read`);
      } catch (_) {
        /* ignore */
      }
    }
    if (item.order_id) {
      router.push(`/orders/${item.order_id}`);
      return;
    }
    if (item.model_uuid) {
      router.push(`/models/${item.model_uuid}`);
      return;
    }
    await load();
  }

  async function markAllRead() {
    try {
      await api.post('/user/notifications/read-all');
      notifications.show({ color: 'teal', message: 'Все прочитаны' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }

  async function clearAll() {
    try {
      await api.delete('/user/notifications');
      notifications.show({ color: 'teal', message: 'Inbox очищен' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }

  return (
    <SellerShell>
      <PageHeader
        title="Уведомления"
        description="Inbox push/email событий §19.16"
        action={
          <Group gap="xs">
            <Button variant="light" leftSection={<IconCheck size={16} />} onClick={() => void markAllRead()} disabled={unread === 0}>
              Прочитать все
            </Button>
            <Button variant="light" color="red" leftSection={<IconTrash size={16} />} onClick={() => void clearAll()} disabled={items.length === 0}>
              Очистить
            </Button>
          </Group>
        }
      />

      <Surface>
        {loading ? (
          <Text c="#6d6c77">Загрузка…</Text>
        ) : items.length === 0 ? (
          <EmptyState title="Нет уведомлений" hint="События заказов, возвратов и модерации появятся здесь" />
        ) : (
          <Stack gap="sm">
            {items.map((item) => {
              const Icon = iconFor(item.type);
              return (
                <Group
                  key={item.id}
                  wrap="nowrap"
                  align="flex-start"
                  p="md"
                  style={{
                    borderRadius: 12,
                    border: '1px solid #ececef',
                    background: item.read ? '#fff' : 'rgba(99, 102, 241, 0.04)',
                    cursor: 'pointer',
                  }}
                  onClick={() => void openItem(item)}
                >
                  <ThemeIcon variant="light" color={iconColor(item.type)} size="lg" radius="md">
                    <Icon size={18} />
                  </ThemeIcon>
                  <Stack gap={4} style={{ flex: 1, minWidth: 0 }}>
                    <Group justify="space-between" wrap="nowrap" gap="xs">
                      <Text fw={item.read ? 500 : 700} size="sm" lineClamp={1}>
                        {item.title}
                      </Text>
                      {!item.read && (
                        <Badge size="xs" color="brand">
                          новое
                        </Badge>
                      )}
                    </Group>
                    {item.body ? (
                      <Text size="sm" c="#6d6c77" lineClamp={2}>
                        {item.body}
                      </Text>
                    ) : null}
                    <Group gap="xs">
                      {item.created_at ? (
                        <Text size="xs" c="#6d6c77">
                          {new Date(item.created_at).toLocaleString('ru-RU')}
                        </Text>
                      ) : null}
                      {item.order_id ? (
                        <Text component={Link} href={`/orders/${item.order_id}`} size="xs" c="brand" onClick={(e) => e.stopPropagation()}>
                          Заказ #{item.order_id}
                        </Text>
                      ) : null}
                      {item.model_uuid ? (
                        <Text component={Link} href={`/models/${item.model_uuid}`} size="xs" c="brand" onClick={(e) => e.stopPropagation()}>
                          Модель
                        </Text>
                      ) : null}
                    </Group>
                  </Stack>
                  {(item.order_id || item.model_uuid) && (
                    <ActionIcon variant="subtle" aria-label="Открыть">
                      →
                    </ActionIcon>
                  )}
                </Group>
              );
            })}
          </Stack>
        )}
      </Surface>
    </SellerShell>
  );
}
