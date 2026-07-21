'use client';

import { Badge, Button, Group, Pagination, SegmentedControl, Select, Text, TextInput, Table } from '@mantine/core';
import { IconPlus, IconSearch } from '@tabler/icons-react';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useMediaQuery } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { SellerShell } from '../../components/SellerShell';
import { ModelsGridView } from '../../components/ModelsGridView';
import { EmptyState, FilterRow, PageHeader, ScrollTable, Surface } from '../../components/ui';
import { api, apiMessage } from '../../services/api';
import { useModelsList } from '../../hooks/useModelsList';

type Model = {
  uuid: string;
  order_id: number;
  display_name?: string | null;
  category?: string | null;
  tier?: string | null;
  user_id?: number;
  glb_url?: string | null;
  publish_status?: string;
  order_status?: string | null;
  created_at?: string;
};

type ModelsResponse = {
  items: Model[];
  total: number;
  limit: number;
  offset: number;
};

type CompanyCtx = {
  id: number;
  role: string;
};

type Member = {
  user_id: number;
  email?: string | null;
  full_name?: string | null;
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

const PUBLISH_FILTER_OPTIONS = [
  { value: 'published', label: 'Опубликованные' },
  { value: 'draft', label: 'Черновики / не опубликовано' },
];

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
  if (status.includes('verified')) return 'Верифицировано';
  if (status.includes('published')) return 'Опубликовано';
  if (status === 'not_published') return 'Не опубликовано';
  return status;
}

const MANAGE_ROLES = new Set(['owner', 'manager']);
const PAGE_SIZE = 20;

export default function ModelsPage() {
  const [page, setPage] = useState(1);
  const [q, setQ] = useState('');
  const [search, setSearch] = useState('');
  const [publishFilter, setPublishFilter] = useState<string | null>(null);
  const [category, setCategory] = useState<string | null>(null);
  const [tier, setTier] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [authorId, setAuthorId] = useState<string | null>(null);
  const [sort, setSort] = useState<string | null>('newest');
  const [isOwner, setIsOwner] = useState(false);
  const [massBusy, setMassBusy] = useState(false);
  const [company, setCompany] = useState<CompanyCtx | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const isMobile = useMediaQuery('(max-width: 767px)');
  const [viewMode, setViewMode] = useState<'table' | 'grid'>('table');

  const { data: modelsData, isLoading: loading, refetch } = useModelsList(
    {
      companyId: company?.id,
      page,
      pageSize: PAGE_SIZE,
      search,
      publishFilter,
      category,
      tier,
      dateFrom,
      dateTo,
      authorId,
      sort,
    },
    company != null,
  );
  const items = (modelsData?.items ?? []) as Model[];
  const total = modelsData?.total ?? 0;

  const canFilterAuthors = company != null && MANAGE_ROLES.has(company.role);
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const useVirtualGrid = viewMode === 'grid' && (total > 100 || items.length > 100);

  useEffect(() => {
    const saved = localStorage.getItem('models_view_mode');
    if (saved === 'grid' || saved === 'table') setViewMode(saved);
  }, []);

  useEffect(() => {
    if (isMobile) setViewMode('grid');
  }, [isMobile]);

  const onViewModeChange = (value: string) => {
    const mode = value === 'grid' ? 'grid' : 'table';
    setViewMode(mode);
    localStorage.setItem('models_view_mode', mode);
  };

  useEffect(() => {
    const t = setTimeout(() => setSearch(q.trim()), 400);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    setPage(1);
  }, [search, publishFilter, category, tier, dateFrom, dateTo, authorId, sort, company]);

  useEffect(() => {
    api
      .get<{ items: Array<{ id: number; role?: string }> }>('/company/mine')
      .then(({ data }) => {
        const first = data.items?.[0];
        if (first?.id) {
          setCompany({ id: first.id, role: first.role || 'member' });
          setIsOwner(first.role === 'owner');
        }
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!canFilterAuthors) return;
    api
      .get<{ items: Member[] }>('/company/members')
      .then(({ data }) => setMembers(data.items ?? []))
      .catch(() => undefined);
  }, [canFilterAuthors]);

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
      void refetch();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setMassBusy(false);
    }
  }

  const memberLabel = useMemo(() => {
    const map = new Map<number, string>();
    for (const m of members) {
      map.set(m.user_id, m.full_name || m.email || `#${m.user_id}`);
    }
    return map;
  }, [members]);

  return (
    <SellerShell>
      <PageHeader
        title="Мои модели"
        description="История генераций · скачивание GLB/USDZ · публикация WB/Ozon"
        action={
          <Group gap="sm">
            <Badge variant="light" color="brand">
              {total} моделей
            </Badge>
            <Button component={Link} href="/models/trash" variant="light" visibleFrom="xs">
              Корзина
            </Button>
            {isOwner && (
              <>
                <Button component={Link} href="/models/import" variant="light" visibleFrom="xs">
                  Импорт GLB
                </Button>
                <Button component={Link} href="/models/import/bulk" variant="light" visibleFrom="xs">
                  Массовый импорт
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
            placeholder="Название или UUID"
            leftSection={<IconSearch size={16} />}
            value={q}
            onChange={(e) => setQ(e.currentTarget.value)}
          />
          <TextInput
            label="Дата от"
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.currentTarget.value)}
          />
          <TextInput
            label="Дата до"
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.currentTarget.value)}
          />
          <Select
            label="Публикация"
            placeholder="Все"
            clearable
            value={publishFilter}
            onChange={setPublishFilter}
            data={PUBLISH_FILTER_OPTIONS}
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
          <Select
            label="Сортировка"
            data={[
              { value: 'newest', label: 'Сначала новые' },
              { value: 'oldest', label: 'Сначала старые' },
            ]}
            value={sort}
            onChange={setSort}
          />
          {canFilterAuthors && (
            <Select
              label="Автор"
              placeholder="Все"
              clearable
              value={authorId}
              onChange={setAuthorId}
              data={members.map((m) => ({
                value: String(m.user_id),
                label: memberLabel.get(m.user_id) || `#${m.user_id}`,
              }))}
            />
          )}
        </FilterRow>

        <Group justify="flex-end" mb="md">
          <SegmentedControl
            value={viewMode}
            onChange={onViewModeChange}
            data={[
              { label: 'Таблица', value: 'table' },
              { label: 'Сетка', value: 'grid' },
            ]}
          />
        </Group>

        {!loading && items.length === 0 ? (
          <EmptyState
            title="Моделей пока нет"
            hint="Создайте заказ с 12 ракурсами или снимите товар в приложении"
            actionLabel="Создать заказ"
            actionHref="/orders/new"
          />
        ) : viewMode === 'grid' ? (
          <>
            <ModelsGridView
              items={items}
              publishBadgeColor={publishBadgeColor}
              publishLabel={publishLabel}
              virtualized={useVirtualGrid}
            />
            {totalPages > 1 && (
              <Group justify="center" mt="md">
                <Pagination total={totalPages} value={page} onChange={setPage} />
              </Group>
            )}
          </>
        ) : (
          <>
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
                  {items.map((m) => (
                    <Table.Tr key={m.uuid}>
                      <Table.Td>
                        <Text fw={600}>{m.display_name || `${m.uuid.slice(0, 8)}…`}</Text>
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
