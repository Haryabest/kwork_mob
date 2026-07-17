'use client';

import { Badge, Button, Group, Pagination, Table, Text } from '@mantine/core';
import { IconArrowBack, IconTrash } from '@tabler/icons-react';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { notifications } from '@mantine/notifications';
import { SellerShell } from '../../../components/SellerShell';
import { EmptyState, PageHeader, ScrollTable, Surface } from '../../../components/ui';
import { api, apiMessage } from '../../../services/api';

type TrashItem = {
  uuid: string;
  order_id: number;
  publish_status?: string;
  trashed_at?: string | null;
  purge_at?: string | null;
  created_at?: string | null;
};

type TrashResponse = {
  items: TrashItem[];
  total: number;
  limit: number;
  offset: number;
};

const PAGE_SIZE = 20;

/** Корзина моделей 30 дней §3.3.1 */
export default function ModelsTrashPage() {
  const [items, setItems] = useState<TrashItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<TrashResponse>('/models/trash', {
        params: { limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE },
      });
      setItems(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    void load();
  }, [load]);

  async function restore(uuid: string) {
    setBusy(uuid);
    try {
      await api.post(`/models/${uuid}/restore-from-trash`);
      notifications.show({ color: 'teal', message: 'Восстановлено из корзины' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(null);
    }
  }

  return (
    <SellerShell>
      <PageHeader
        title="Корзина"
        description="Модели хранятся 30 дней · восстановление без оплаты (§3.3.1)"
        action={
          <Button component={Link} href="/models" variant="light">
            К моделям
          </Button>
        }
      />
      <Surface>
        {loading ? (
          <Text c="dimmed">Загрузка…</Text>
        ) : items.length === 0 ? (
          <EmptyState title="Корзина пуста" description="Удалённые модели появятся здесь на 30 дней" />
        ) : (
          <>
            <ScrollTable>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>UUID</Table.Th>
                    <Table.Th>Заказ</Table.Th>
                    <Table.Th>В корзине</Table.Th>
                    <Table.Th>Удаление</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {items.map((m) => (
                    <Table.Tr key={m.uuid}>
                      <Table.Td>
                        <Text size="sm" ff="monospace">
                          {m.uuid.slice(0, 8)}…
                        </Text>
                      </Table.Td>
                      <Table.Td>#{m.order_id}</Table.Td>
                      <Table.Td>{m.trashed_at ? m.trashed_at.slice(0, 10) : '—'}</Table.Td>
                      <Table.Td>
                        <Badge variant="light" color="orange">
                          {m.purge_at ? m.purge_at.slice(0, 10) : '—'}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Group gap="xs">
                          <Button
                            size="xs"
                            variant="light"
                            leftSection={<IconArrowBack size={14} />}
                            loading={busy === m.uuid}
                            onClick={() => void restore(m.uuid)}
                          >
                            Восстановить
                          </Button>
                          <Button
                            size="xs"
                            component={Link}
                            href={`/models/${m.uuid}`}
                            variant="subtle"
                            leftSection={<IconTrash size={14} />}
                          >
                            Карточка
                          </Button>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </ScrollTable>
            {totalPages > 1 && (
              <Group justify="center" mt="md">
                <Pagination total={totalPages} value={page} onChange={setPage} />
              </Group>
            )}
          </>
        )}
      </Surface>
    </SellerShell>
  );
}
