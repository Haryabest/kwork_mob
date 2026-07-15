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
  category?: string | null;
  tier?: string | null;
  glb_url?: string | null;
  publish_status?: string;
  order_status?: string | null;
  created_at?: string;
};

const CATEGORY_OPTIONS = [
  { value: 'clothing', label: 'Одежда' },
  { value: 'shoes', label: 'Обувь' },
  { value: 'electronics', label: 'Электроника' },
  { value: 'furniture', label: 'Мебель' },
  { value: 'decor', label: 'Декор' },
  { value: 'toys', label: 'Игрушки' },
  { value: 'adult', label: '18+' },
  { value: 'other', label: 'Другое' },
];

const CATEGORY_LABEL: Record<string, string> = Object.fromEntries(
  CATEGORY_OPTIONS.map((c) => [c.value, c.label]),
);

const PUBLISH_LABEL: Record<string, string> = {
  not_published: 'Не опубликовано',
  pending_verify: 'На проверке',
  published: 'Опубликовано',
  rejected: 'Отклонено',
  import_validating: 'Проверка импорта',
  imported: 'Импортировано',
  import_failed: 'Ошибка импорта',
};

function publishBadgeColor(status?: string | null, orderStatus?: string | null): string {
  if (orderStatus === 'blocked_nsfw') return 'red';
  switch (status) {
    case 'import_validating':
      return 'blue';
    case 'imported':
      return 'teal';
    case 'import_failed':
      return 'red';
    case 'rejected':
      return 'red';
    case 'pending_verify':
      return 'yellow';
    case 'published':
      return 'green';
    default:
      if (status?.includes('published') || status?.includes('verified')) return 'teal';
      return 'brand';
  }
}

function publishLabel(status?: string | null, orderStatus?: string | null): string {
  if (orderStatus === 'blocked_nsfw') return 'NSFW блок';
  if (!status) return '—';
  if (PUBLISH_LABEL[status]) return PUBLISH_LABEL[status];
  if (status.includes('verified')) return 'Верифицировано';
  if (status.includes('published')) return 'Опубликовано';
  return status;
}

export default function ModelsPage() {
  const [items, setItems] = useState<Model[]>([]);
  const [q, setQ] = useState('');
  const [status, setStatus] = useState<string | null>(null);
  const [category, setCategory] = useState<string | null>(null);
  const [tier, setTier] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isOwner, setIsOwner] = useState(false);
  const [massBusy, setMassBusy] = useState(false);

  useEffect(() => {
    api
      .get<{ items: Model[] }>('/user/models')
      .then(({ data }) => setItems(data.items ?? []))
      .catch((e) => notifications.show({ color: 'red', message: apiMessage(e) }))
      .finally(() => setLoading(false));
    api
      .get<{ items: Array<{ role?: string }> }>('/company/mine')
      .then(({ data }) => setIsOwner((data.items ?? []).some((c) => c.role === 'owner')))
      .catch(() => undefined);
  }, []);

  async function massExtendAll() {
    if (!window.confirm('Продлить хранение исходников для всех моделей компании? (лимит 3× на модель)')) {
      return;
    }
    setMassBusy(true);
    try {
      const { data } = await api.post<{ message?: string; extended?: number }>(
        '/company/models/mass-extend-storage',
      );
      notifications.show({
        color: 'teal',
        message: data.message || `Продлено: ${data.extended ?? 0}`,
      });
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setMassBusy(false);
    }
  }

  const filtered = useMemo(() => {
    return items.filter((m) => {
      if (status && m.publish_status !== status) return false;
      if (category && m.category !== category) return false;
      if (tier && m.tier !== tier) return false;
      if (q && !m.uuid.includes(q) && !String(m.order_id).includes(q)) return false;
      return true;
    });
  }, [items, q, status, category, tier]);

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
            {isOwner && (
              <>
                <Button component={Link} href="/models/import" variant="light" visibleFrom="xs">
                  Импорт GLB
                </Button>
                <Button variant="light" loading={massBusy} onClick={() => void massExtendAll()} visibleFrom="xs">
                  Продлить все исходники
                </Button>
              </>
            )}
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
          <Select
            label="Категория"
            placeholder="Все"
            data={CATEGORY_OPTIONS}
            clearable
            value={category}
            onChange={setCategory}
          />
          <Select
            label="Тариф"
            placeholder="Все"
            data={[
              { value: 'small', label: 'Small' },
              { value: 'large', label: 'Large' },
            ]}
            clearable
            value={tier}
            onChange={setTier}
          />
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
                  <Table.Th>Категория</Table.Th>
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
                    <Table.Td>{CATEGORY_LABEL[m.category || ''] || m.category || '—'}</Table.Td>
                    <Table.Td>{m.created_at ? new Date(m.created_at).toLocaleString('ru-RU') : '—'}</Table.Td>
                    <Table.Td>
                      <Badge variant="light" color={publishBadgeColor(m.publish_status, m.order_status)}>
                        {publishLabel(m.publish_status, m.order_status)}
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
