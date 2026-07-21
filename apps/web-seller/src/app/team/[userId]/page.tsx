'use client';

import {
  Badge,
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { notifications } from '@mantine/notifications';
import { SellerShell } from '../../../components/SellerShell';
import { PageHeader, ScrollTable, SubNav, Surface } from '../../../components/ui';
import { api, apiMessage } from '../../../services/api';

type Member = {
  user_id: number;
  email?: string | null;
  full_name?: string | null;
  role: string;
  max_concurrent_orders?: number | null;
  monthly_spending_limit?: number | null;
  allowed_categories?: string[] | null;
};

type TaskRow = {
  id: number;
  status?: string;
  category?: string;
  tier?: string;
  amount?: number;
  created_at?: string;
};

type SessionRow = {
  id: number;
  created_at?: string | null;
  expires_at?: string | null;
};

type AuditRow = {
  id: number;
  action: string;
  details?: Record<string, unknown>;
  created_at?: string | null;
};

export default function TeamMemberDetailPage() {
  const params = useParams<{ userId: string }>();
  const userId = Number(params.userId);
  const router = useRouter();
  const [member, setMember] = useState<Member | null>(null);
  const [tasks, setTasks] = useState<TaskRow[]>([]);
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [roleOpen, roleHandlers] = useDisclosure(false);
  const [limitsOpen, limitsHandlers] = useDisclosure(false);
  const [role, setRole] = useState<string | null>('photographer');
  const [limitOrders, setLimitOrders] = useState<number | string>(3);
  const [limitSpend, setLimitSpend] = useState<number | string>('');

  const load = useCallback(async () => {
    try {
      const [mRes, tRes, sRes, aRes] = await Promise.all([
        api.get<Member>(`/company/members/${userId}`),
        api.get<{ items: TaskRow[] }>(`/company/members/${userId}/tasks`),
        api.get<{ items: SessionRow[] }>(`/company/members/${userId}/sessions`),
        api.get<{ items: AuditRow[] }>('/company/audit', { params: { user_id: userId, limit: 50 } }),
      ]);
      setMember(mRes.data);
      setTasks(tRes.data.items || []);
      setSessions(sRes.data.items || []);
      setAudit(aRes.data.items || []);
      setRole(mRes.data.role);
      setLimitOrders(mRes.data.max_concurrent_orders ?? 3);
      setLimitSpend(mRes.data.monthly_spending_limit ?? '');
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }, [userId]);

  useEffect(() => {
    void load();
  }, [load]);

  const stats = {
    orders: tasks.length,
    amount: tasks.reduce((s, t) => s + (t.amount || 0), 0),
  };

  async function saveRole() {
    if (!role) return;
    setBusy(true);
    try {
      await api.patch(`/company/members/${userId}/role`, { role });
      notifications.show({ color: 'teal', message: 'Роль обновлена' });
      roleHandlers.close();
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function saveLimits() {
    setBusy(true);
    try {
      await api.patch(`/company/members/${userId}/limits`, {
        max_concurrent_orders: Number(limitOrders) || null,
        monthly_spending_limit: limitSpend === '' ? null : Number(limitSpend),
      });
      notifications.show({ color: 'teal', message: 'Лимиты обновлены' });
      limitsHandlers.close();
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function revokeSessions() {
    setBusy(true);
    try {
      await api.post(`/company/members/${userId}/sessions/revoke`);
      notifications.show({ color: 'teal', message: 'Сессии отозваны' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function removeMember() {
    if (!confirm('Удалить сотрудника из команды?')) return;
    setBusy(true);
    try {
      await api.delete(`/company/members/${userId}`);
      notifications.show({ color: 'teal', message: 'Сотрудник удалён' });
      router.push('/team');
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  if (!member) {
    return (
      <SellerShell>
        <Text c="dimmed">Загрузка…</Text>
      </SellerShell>
    );
  }

  return (
    <SellerShell>
      <SubNav items={[{ href: '/team', label: '← К команде' }]} />
      <PageHeader
        title={member.full_name || member.email || `User #${userId}`}
        description={`${member.email || ''} · роль ${member.role}`}
        action={<Badge variant="light">{member.role}</Badge>}
      />

      <Surface mb="md">
        <Stack gap="sm">
          <Text fw={600}>Профиль</Text>
          <Text size="sm">Email: {member.email || '—'}</Text>
          <Text size="sm">Роль: {member.role}</Text>
          <Text size="sm">
            Лимиты: заказов {member.max_concurrent_orders ?? '—'}, бюджет{' '}
            {member.monthly_spending_limit != null ? `${member.monthly_spending_limit} ₽` : '—'}
          </Text>
          <Text size="sm">
            Категории: {(member.allowed_categories || []).join(', ') || 'все'}
          </Text>
          <Group>
            <Button variant="light" size="xs" onClick={roleHandlers.open}>
              Изменить роль
            </Button>
            <Button variant="light" size="xs" onClick={limitsHandlers.open}>
              Лимиты
            </Button>
            <Button variant="light" size="xs" color="orange" loading={busy} onClick={() => void revokeSessions()}>
              Отозвать сессии
            </Button>
            <Button variant="light" size="xs" color="red" loading={busy} onClick={() => void removeMember()}>
              Удалить
            </Button>
          </Group>
        </Stack>
      </Surface>

      <Surface mb="md">
        <Text fw={600} mb="sm">
          Статистика
        </Text>
        <Group>
          <Badge variant="light">Заказов: {stats.orders}</Badge>
          <Badge variant="light">Сумма: {stats.amount.toLocaleString('ru-RU')} ₽</Badge>
        </Group>
      </Surface>

      <Surface mb="md">
        <Text fw={600} mb="sm">
          Заказы сотрудника
        </Text>
        <ScrollTable>
          <Table miw={640}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>#</Table.Th>
                <Table.Th>Статус</Table.Th>
                <Table.Th>Категория</Table.Th>
                <Table.Th>Сумма</Table.Th>
                <Table.Th>Дата</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {tasks.map((t) => (
                <Table.Tr key={t.id}>
                  <Table.Td>
                    <Button component={Link} href={`/orders/${t.id}`} variant="subtle" size="xs">
                      #{t.id}
                    </Button>
                  </Table.Td>
                  <Table.Td>{t.status || '—'}</Table.Td>
                  <Table.Td>{t.category || '—'}</Table.Td>
                  <Table.Td>{t.amount != null ? `${t.amount} ₽` : '—'}</Table.Td>
                  <Table.Td>{t.created_at ? new Date(t.created_at).toLocaleString('ru-RU') : '—'}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </ScrollTable>
      </Surface>

      <Surface mb="md">
        <Text fw={600} mb="sm">
          Аудит
        </Text>
        <ScrollTable>
          <Table miw={560}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Действие</Table.Th>
                <Table.Th>Дата</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {audit.map((a) => (
                <Table.Tr key={a.id}>
                  <Table.Td>{a.action}</Table.Td>
                  <Table.Td>{a.created_at ? new Date(a.created_at).toLocaleString('ru-RU') : '—'}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </ScrollTable>
      </Surface>

      <Surface>
        <Text fw={600} mb="sm">
          Активные сессии
        </Text>
        <ScrollTable>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Создана</Table.Th>
                <Table.Th>Истекает</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {sessions.map((s) => (
                <Table.Tr key={s.id}>
                  <Table.Td>{s.id}</Table.Td>
                  <Table.Td>{s.created_at ? new Date(s.created_at).toLocaleString('ru-RU') : '—'}</Table.Td>
                  <Table.Td>{s.expires_at ? new Date(s.expires_at).toLocaleString('ru-RU') : '—'}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </ScrollTable>
      </Surface>

      <Modal opened={roleOpen} onClose={roleHandlers.close} title="Роль сотрудника" centered>
        <Stack>
          <Select
            label="Роль"
            data={['owner', 'manager', 'photographer', 'viewer']}
            value={role}
            onChange={setRole}
          />
          <Button loading={busy} onClick={() => void saveRole()}>
            Сохранить
          </Button>
        </Stack>
      </Modal>

      <Modal opened={limitsOpen} onClose={limitsHandlers.close} title="Лимиты" centered>
        <Stack>
          <NumberInput label="Параллельных заказов" value={limitOrders} onChange={setLimitOrders} min={1} max={20} />
          <NumberInput label="Лимит трат / мес, ₽" value={limitSpend} onChange={setLimitSpend} min={0} />
          <Button loading={busy} onClick={() => void saveLimits()}>
            Сохранить
          </Button>
        </Stack>
      </Modal>
    </SellerShell>
  );
}
