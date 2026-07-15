'use client';

import {
  Badge,
  Button,
  Center,
  Group,
  Loader,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
} from '@mantine/core';
import { IconDownload, IconPlus } from '@tabler/icons-react';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { SellerShell } from '../../components/SellerShell';
import { EmptyState, FilterRow, PageHeader, ScrollTable, Surface } from '../../components/ui';
import { api, apiMessage } from '../../services/api';

type Tx = {
  id: number;
  user_id?: number;
  amount: number;
  type: string;
  description?: string;
  created_at?: string;
};

type Member = {
  user_id: number;
  email?: string | null;
  full_name?: string | null;
  role?: string;
};

const MANAGE_ROLES = new Set(['owner', 'manager']);

/** §20.3 / §8 — баланс и транзакции (личный или компания) */
export default function BalancePage() {
  const [opened, { open, close }] = useDisclosure(false);
  const [balance, setBalance] = useState(0);
  const [items, setItems] = useState<Tx[]>([]);
  const [amount, setAmount] = useState<number | string>(1000);
  const [loading, setLoading] = useState(true);
  const [paying, setPaying] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [corporate, setCorporate] = useState(false);
  const [isOwner, setIsOwner] = useState(false);
  const [canFilterAuthors, setCanFilterAuthors] = useState(false);
  const [members, setMembers] = useState<Member[]>([]);
  const [authorId, setAuthorId] = useState<string | null>(null);

  const memberLabel = useMemo(() => {
    const map = new Map<number, string>();
    for (const m of members) {
      map.set(m.user_id, m.full_name || m.email || `#${m.user_id}`);
    }
    return map;
  }, [members]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const mine = await api.get<{
        items: Array<{ id: number; role?: string; balance?: number | null; is_owner?: boolean }>;
      }>('/company/mine');
      const company = mine.data.items?.[0];
      const role = company?.role ?? '';
      const useCorporate = Boolean(company?.id && company.balance != null);
      setCorporate(useCorporate);
      setIsOwner(role === 'owner' || company?.is_owner === true);
      setCanFilterAuthors(MANAGE_ROLES.has(role));

      if (useCorporate && company) {
        setBalance(company.balance ?? 0);
        const params: Record<string, string | number> = {};
        if (authorId) params.user_id = Number(authorId);
        const tx = await api.get<{ items: Tx[] }>('/company/transactions', { params });
        setItems(tx.data.items ?? []);
        if (MANAGE_ROLES.has(role)) {
          const mem = await api.get<{ items: Member[] }>('/company/members');
          setMembers(mem.data.items ?? []);
        }
      } else {
        const [me, tx] = await Promise.all([
          api.get<{ balance: number }>('/user/me'),
          api.get<{ items: Tx[] }>('/user/transactions'),
        ]);
        setBalance(me.data.balance ?? 0);
        setItems(tx.data.items ?? []);
      }
      setUpdatedAt(new Date());
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setLoading(false);
    }
  }, [authorId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function topup() {
    const value = typeof amount === 'number' ? amount : Number(amount);
    if (!value || value < 100) {
      notifications.show({ color: 'red', message: 'Минимум 100 ₽' });
      return;
    }
    setPaying(true);
    try {
      const endpoint = corporate && isOwner ? '/company/balance/topup' : '/user/balance/topup';
      const { data } = await api.post<{
        confirmation_url?: string;
        status?: string;
        dev_mock?: boolean;
        balance?: number;
      }>(endpoint, {
        amount: value,
      });
      if (data.confirmation_url) {
        window.location.href = data.confirmation_url;
        return;
      }
      if (data.dev_mock || data.status === 'succeeded') {
        if (typeof data.balance === 'number') setBalance(data.balance);
        notifications.show({ color: 'green', message: 'Баланс пополнен (локальный режим)' });
        close();
        await load();
        return;
      }
      notifications.show({ color: 'yellow', message: 'Нет confirmation_url от ЮKassa' });
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e, 'Не удалось создать платёж') });
    } finally {
      setPaying(false);
    }
  }

  async function exportCsv() {
    if (corporate && isOwner) {
      try {
        const params: Record<string, string | number> = {};
        if (authorId) params.user_id = Number(authorId);
        const res = await api.get('/company/transactions/export', {
          params,
          responseType: 'blob',
        });
        const blob = new Blob([res.data as BlobPart], { type: 'text/csv;charset=utf-8' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'company_transactions.csv';
        a.click();
        return;
      } catch (e) {
        notifications.show({ color: 'red', message: apiMessage(e, 'Не удалось выгрузить CSV') });
        return;
      }
    }
    const rows = [
      ['id', 'user_id', 'date', 'type', 'amount', 'description'],
      ...items.map((t) => [
        String(t.id),
        t.user_id != null ? String(t.user_id) : '',
        t.created_at ?? '',
        t.type,
        String(t.amount),
        t.description ?? '',
      ]),
    ];
    const blob = new Blob(
      [rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n')],
      { type: 'text/csv;charset=utf-8' },
    );
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'transactions.csv';
    a.click();
  }

  return (
    <SellerShell>
      <PageHeader
        title={corporate ? 'Баланс компании' : 'Баланс и пополнение'}
        description={
          corporate
            ? 'Корпоративный счёт · история списаний §8'
            : 'ЮKassa · СБП и карта · история операций'
        }
        action={
          corporate && isOwner ? (
            <Button leftSection={<IconPlus size={16} />} onClick={open}>
              Пополнить баланс компании
            </Button>
          ) : !corporate ? (
            <Button leftSection={<IconPlus size={16} />} onClick={open}>
              Пополнить баланс
            </Button>
          ) : undefined
        }
      />

      {loading ? (
        <Center py="xl">
          <Loader color="brand" />
        </Center>
      ) : (
        <Surface>
          <Group justify="space-between" align="flex-end" wrap="wrap" gap="lg" mb="xl">
            <div>
              <Text size="sm" c="#6d6c77">
                Текущий баланс
              </Text>
              <Text fw={700} fz={{ base: 32, sm: 40 }} className="vz-metric-value" mt={6}>
                {balance.toLocaleString('ru-RU')} ₽
              </Text>
              <Text size="xs" c="#6d6c77" mt={8}>
                Обновлено:{' '}
                {updatedAt
                  ? updatedAt.toLocaleString('ru-RU', {
                      day: '2-digit',
                      month: '2-digit',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  : '—'}
              </Text>
            </div>
            <Button variant="light" leftSection={<IconDownload size={16} />} onClick={() => void exportCsv()}>
              Экспорт CSV
            </Button>
          </Group>

          {corporate && canFilterAuthors && (
            <FilterRow mb="md">
              <Select
                label="Сотрудник §8"
                placeholder="Все"
                clearable
                searchable
                value={authorId}
                onChange={setAuthorId}
                data={members.map((m) => ({
                  value: String(m.user_id),
                  label: memberLabel.get(m.user_id) || String(m.user_id),
                }))}
              />
            </FilterRow>
          )}

          <Text fw={700} mb="md">
            История транзакций
          </Text>

          {items.length === 0 ? (
            <EmptyState title="Транзакций пока нет" hint="Пополните баланс, чтобы создавать заказы на генерацию" />
          ) : (
            <ScrollTable>
              <Table verticalSpacing="md" miw={640}>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Дата</Table.Th>
                    {corporate && canFilterAuthors && <Table.Th>Сотрудник</Table.Th>}
                    <Table.Th>Тип</Table.Th>
                    <Table.Th>Сумма</Table.Th>
                    <Table.Th>Описание</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {items.map((t) => (
                    <Table.Tr key={t.id}>
                      <Table.Td>
                        {t.created_at ? new Date(t.created_at).toLocaleString('ru-RU') : '—'}
                      </Table.Td>
                      {corporate && canFilterAuthors && (
                        <Table.Td>{memberLabel.get(t.user_id || 0) || t.user_id || '—'}</Table.Td>
                      )}
                      <Table.Td>
                        <Badge variant="light" color="brand">
                          {t.type}
                        </Badge>
                      </Table.Td>
                      <Table.Td fw={700} c={t.amount >= 0 ? 'teal' : 'red'}>
                        {t.amount >= 0 ? '+' : ''}
                        {t.amount.toLocaleString('ru-RU')} ₽
                      </Table.Td>
                      <Table.Td>{t.description || '—'}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </ScrollTable>
          )}
        </Surface>
      )}

      <Modal
        opened={opened}
        onClose={close}
        title={corporate && isOwner ? 'Пополнить баланс компании' : 'Пополнить баланс'}
        centered
        radius="lg"
        padding="lg"
      >
        <Stack gap="md">
          <Text size="sm" c="#6d6c77">
            Оплата через ЮKassa (карта / СБП). После оплаты вернётесь на эту страницу.
          </Text>
          <NumberInput label="Сумма, ₽" min={100} max={500000} value={amount} onChange={setAmount} size="md" />
          <Button loading={paying} onClick={() => void topup()} fullWidth size="md">
            Перейти к оплате
          </Button>
        </Stack>
      </Modal>
    </SellerShell>
  );
}
