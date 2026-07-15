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
import { useCallback, useEffect, useMemo, useState } from 'react';
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
  user_id?: number;
  created_at?: string;
};

type CompanyCtx = {
  id: number;
  role: string;
};

type Member = {
  user_id: number;
  email?: string | null;
  full_name?: string | null;
  role?: string;
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
  blocked_nsfw: 'NSFW блок',
};

const STATUS_COLOR: Record<string, string> = {
  completed: 'teal',
  processing: 'blue',
  queued: 'cyan',
  awaiting_payment: 'orange',
  failed: 'red',
  cancelled: 'gray',
  blocked_nsfw: 'red',
};

const MANAGE_ROLES = new Set(['owner', 'manager']);

// Незавершённые статусы — пока есть такие заказы, список опрашивается вживую.
const ACTIVE_STATUSES = new Set([
  'pending',
  'awaiting_payment',
  'paid',
  'queued',
  'processing',
]);
const LIVE_POLL_MS = 15000;

/** §20.6 Заказы · §3.16.2 фильтр исполнитель */
export default function OrdersPage() {
  const [items, setItems] = useState<OrderItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');
  const [status, setStatus] = useState<string | null>(null);
  const [authorId, setAuthorId] = useState<string | null>(null);
  const [company, setCompany] = useState<CompanyCtx | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  const canFilterAuthors = company != null && MANAGE_ROLES.has(company.role);

  const loadOrders = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true);
      try {
        const params: Record<string, string | number> = {};
        if (company) params.company_id = company.id;
        if (authorId) params.user_id = Number(authorId);
        const { data } = await api.get<{ items: OrderItem[] }>('/orders', { params });
        setItems(data.items ?? []);
        setUpdatedAt(new Date());
      } catch (e) {
        if (!silent) notifications.show({ color: 'red', message: apiMessage(e) });
      } finally {
        if (!silent) setLoading(false);
      }
    },
    [company, authorId],
  );

  useEffect(() => {
    api
      .get<{ items: Array<{ id: number; role?: string }> }>('/company/mine')
      .then(({ data }) => {
        const first = data.items?.[0];
        if (first?.id) {
          setCompany({ id: first.id, role: first.role || 'member' });
        }
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!canFilterAuthors || !company) return;
    api
      .get<{ items: Member[] }>('/company/members')
      .then(({ data }) => setMembers(data.items ?? []))
      .catch(() => undefined);
  }, [canFilterAuthors, company]);

  useEffect(() => {
    void loadOrders();
  }, [loadOrders]);

  const hasActive = useMemo(
    () => items.some((o) => ACTIVE_STATUSES.has(o.status)),
    [items],
  );

  // §20.6 живые статусы: пока есть незавершённые заказы — тихий поллинг.
  useEffect(() => {
    if (!hasActive) return;
    const tick = () => {
      if (typeof document !== 'undefined' && document.visibilityState === 'visible') {
        void loadOrders(true);
      }
    };
    const timer = window.setInterval(tick, LIVE_POLL_MS);
    return () => window.clearInterval(timer);
  }, [hasActive, loadOrders]);

  const memberLabel = useMemo(() => {
    const map = new Map<number, string>();
    for (const m of members) {
      const name = m.full_name || m.email || `user #${m.user_id}`;
      map.set(m.user_id, `${name}${m.role ? ` (${m.role})` : ''}`);
    }
    return map;
  }, [members]);

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
        description={
          company
            ? `Заказы компании · роль ${company.role}`
            : 'Статусы генераций, оплата и очередь'
        }
        action={
          <Button component={Link} href="/orders/new" leftSection={<IconPlus size={16} />}>
            Новый заказ
          </Button>
        }
      />

      <Surface>
        {updatedAt && (
          <Group gap={6} mb="xs">
            <Badge color={hasActive ? 'teal' : 'gray'} variant="dot" size="sm">
              {hasActive ? 'Обновляется автоматически' : 'Актуально'}
            </Badge>
            <Text size="xs" c="dimmed">
              обновлено {updatedAt.toLocaleTimeString('ru-RU')}
            </Text>
          </Group>
        )}
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
          {canFilterAuthors && (
            <Select
              label="Исполнитель §3.16.2"
              placeholder="Все сотрудники"
              clearable
              searchable
              value={authorId}
              onChange={setAuthorId}
              data={members.map((m) => ({
                value: String(m.user_id),
                label: memberLabel.get(m.user_id) || String(m.user_id),
              }))}
            />
          )}
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
            <Table highlightOnHover miw={760} verticalSpacing="md">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Заказ</Table.Th>
                  {canFilterAuthors && <Table.Th>Исполнитель</Table.Th>}
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
                    {canFilterAuthors && (
                      <Table.Td>
                        <Text size="sm" c="dimmed">
                          {memberLabel.get(o.user_id || 0) || (o.user_id ? `#${o.user_id}` : '—')}
                        </Text>
                      </Table.Td>
                    )}
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
