'use client';

import { Badge, Button, Group, Select, Text, TextInput, Table } from '@mantine/core';
import { IconPlus, IconSearch } from '@tabler/icons-react';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { notifications } from '@mantine/notifications';
import { SellerShell } from '../../components/SellerShell';
import { EmptyState, FilterRow, PageHeader, ScrollTable, Surface } from '../../components/ui';
import { api, apiMessage } from '../../services/api';

type Model = {
  uuid: string;
  order_id: number;
  glb_url?: string | null;
  publish_status?: string;
  created_at?: string;
};

const PUBLISH_LABEL: Record<string, string> = {
  not_published: 'Не опубликовано',
  pending_verify: 'На проверке',
  published: 'Опубликовано',
  rejected: 'Отклонено',
};

export default function ModelsPage() {
  const [items, setItems] = useState<Model[]>([]);
  const [q, setQ] = useState('');
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<{ items: Model[] }>('/user/models')
      .then(({ data }) => setItems(data.items ?? []))
      .catch((e) => notifications.show({ color: 'red', message: apiMessage(e) }))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    return items.filter((m) => {
      if (status && m.publish_status !== status) return false;
      if (q && !m.uuid.includes(q) && !String(m.order_id).includes(q)) return false;
      return true;
    });
  }, [items, q, status]);

  return (
    <SellerShell>
      <PageHeader
        title="Мои модели"
        description="История генераций · скачивание GLB/USDZ · публикация WB/Ozon"
        action={
          <Group gap="sm">
            <Badge variant="light" color="brand">
              {items.length} моделей
            </Badge>
            <Button component={Link} href="/models/trash" variant="light" visibleFrom="xs">
              Корзина
            </Button>
            <Button component={Link} href="/orders/new" leftSection={<IconPlus size={16} />} visibleFrom="xs">
              Новая
            </Button>
          </Group>
        }
      />

      <Surface>
        <FilterRow>
          <TextInput
            label="Поиск"
            placeholder="UUID или заказ"
            leftSection={<IconSearch size={16} />}
            value={q}
            onChange={(e) => setQ(e.currentTarget.value)}
          />
          <Select
            label="Публикация"
            placeholder="Все"
            clearable
            value={status}
            onChange={setStatus}
            data={Object.entries(PUBLISH_LABEL).map(([value, label]) => ({ value, label }))}
          />
          <Select label="Категория" placeholder="Все" data={['Одежда', 'Обувь', 'Электроника', 'Другое']} clearable disabled />
          <Select label="Тариф" placeholder="Все" data={['small', 'large']} clearable disabled />
        </FilterRow>

        {!loading && filtered.length === 0 ? (
          <EmptyState
            title="Моделей пока нет"
            hint="Создайте заказ с 12 ракурсами или снимите товар в приложении"
            actionLabel="Создать заказ"
            actionHref="/orders/new"
          />
        ) : (
          <ScrollTable>
            <Table highlightOnHover verticalSpacing="md" miw={720}>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Модель</Table.Th>
                  <Table.Th>Заказ</Table.Th>
                  <Table.Th>Создана</Table.Th>
                  <Table.Th>Публикация</Table.Th>
                  <Table.Th />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {filtered.map((m) => (
                  <Table.Tr key={m.uuid}>
                    <Table.Td>
                      <Text fw={600}>{m.uuid.slice(0, 8)}…</Text>
                    </Table.Td>
                    <Table.Td>#{m.order_id}</Table.Td>
                    <Table.Td>{m.created_at ? new Date(m.created_at).toLocaleString('ru-RU') : '—'}</Table.Td>
                    <Table.Td>
                      <Badge variant="light" color="brand">
                        {PUBLISH_LABEL[m.publish_status || ''] || m.publish_status || '—'}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Button component={Link} href={`/models/${m.uuid}`} size="xs" variant="light">
                        Открыть
                      </Button>
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
