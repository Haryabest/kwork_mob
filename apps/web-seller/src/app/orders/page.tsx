'use client';

import {
  Badge,
  Button,
  Center,
  Group,
  Loader,
  Select,
  Table,
  Text,
  TextInput,
} from '@mantine/core';
import { IconPlus, IconSearch } from '@tabler/icons-react';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { notifications } from '@mantine/notifications';
import { SellerShell } from '../../components/SellerShell';
import { EmptyState, FilterRow, PageHeader, ScrollTable, Surface } from '../../components/ui';
import { api, apiMessage } from '../../services/api';

type OrderItem = {
  id: number;
  task_uuid: string;
  category: string;
  tier: string;
  status: string;
  amount: number;
  created_at?: string;
};

const STATUS_LABEL: Record<string, string> = {
  pending: 'Новый',
  awaiting_payment: 'Ожидает оплаты',
  queued: 'В очереди',
  processing: 'В обработке',
  completed: 'Готов',
  failed: 'Ошибка',
  cancelled: 'Отменён',
  paid: 'Оплачен',
};

const STATUS_COLOR: Record<string, string> = {
  completed: 'teal',
  processing: 'blue',
  queued: 'cyan',
  awaiting_payment: 'orange',
  failed: 'red',
  cancelled: 'gray',
};

/** §20.6 Заказы */
export default function OrdersPage() {
  const [items, setItems] = useState<OrderItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<{ items: OrderItem[] }>('/orders')
      .then(({ data }) => setItems(data.items ?? []))
      .catch((e) => notifications.show({ color: 'red', message: apiMessage(e) }))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    return items.filter((o) => {
      if (status && o.status !== status) return false;
      if (q && !String(o.id).includes(q) && !o.task_uuid.includes(q)) return false;
      return true;
    });
  }, [items, q, status]);

  return (
    <SellerShell>
      <PageHeader
        title="Заказы"
        description="Статусы генераций, оплата и очередь"
        action={
          <Button component={Link} href="/orders/new" leftSection={<IconPlus size={16} />}>
            Новый заказ
          </Button>
        }
      />

      <Surface>
        <FilterRow>
          <TextInput
            label="Поиск"
            placeholder="Номер / UUID"
            leftSection={<IconSearch size={16} />}
            value={q}
            onChange={(e) => setQ(e.currentTarget.value)}
          />
          <Select
            label="Статус"
            placeholder="Все"
            clearable
            value={status}
            onChange={setStatus}
            data={Object.entries(STATUS_LABEL).map(([value, label]) => ({ value, label }))}
          />
        </FilterRow>

        {loading ? (
          <Center py="xl">
            <Loader color="brand" />
          </Center>
        ) : filtered.length === 0 ? (
          <EmptyState
            title="Заказов пока нет"
            hint="Создайте заказ: 12 ракурсов → оплата → генерация"
            actionLabel="Создать заказ"
            actionHref="/orders/new"
          />
        ) : (
          <ScrollTable>
            <Table highlightOnHover miw={680} verticalSpacing="md">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Заказ</Table.Th>
                  <Table.Th>Создан</Table.Th>
                  <Table.Th>Тариф</Table.Th>
                  <Table.Th>Стоимость</Table.Th>
                  <Table.Th>Статус</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {filtered.map((o) => (
                  <Table.Tr key={o.id}>
                    <Table.Td>
                      <Text
                        component={Link}
                        href={`/orders/${o.id}`}
                        fw={700}
                        c="brand"
                        style={{ textDecoration: 'none' }}
                      >
                        #{o.id}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      {o.created_at ? new Date(o.created_at).toLocaleString('ru-RU') : '—'}
                    </Table.Td>
                    <Table.Td>{o.tier}</Table.Td>
                    <Table.Td>{o.amount.toLocaleString('ru-RU')} ₽</Table.Td>
                    <Table.Td>
                      <Badge color={STATUS_COLOR[o.status] || 'gray'} variant="light">
                        {STATUS_LABEL[o.status] || o.status}
                      </Badge>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </ScrollTable>
        )}
      </Surface>
    </SellerShell>
  );
}
