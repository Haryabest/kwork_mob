'use client';

import {
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  CopyButton,
  ActionIcon,
  Tooltip,
  Textarea,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconCheck, IconCopy, IconLink, IconUserPlus } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { QRCodeCanvas } from 'qrcode.react';
import { useCallback, useEffect, useState } from 'react';
import { SellerShell } from '../../components/SellerShell';
import { EmptyState, FilterRow, PageHeader, ScrollTable, SubNav, Surface } from '../../components/ui';
import { api, apiMessage } from '../../services/api';

type Member = {
  user_id: number;
  email?: string | null;
  full_name?: string | null;
  role: string;
};
type Invite = {
  id: number;
  email: string;
  role: string;
  status: string;
  url: string;
  expires_at?: string;
};

type TeamFunnelRow = {
  user_id: number;
  email?: string | null;
  full_name?: string | null;
  funnel: {
    generated: number;
    downloaded: number;
    links_added: number;
    verified: number;
    manual_marked: number;
  };
  avg_days_to_verification?: number | null;
};

type AccessRow = {
  id: number;
  user_id: number;
  model_uuid: string;
  file_format?: string | null;
  ip_address?: string | null;
  timestamp?: string | null;
};

const MEMBER_PAGE = 20;

/** §20.5 Команда + shoot_link Owner */
export default function TeamPage() {
  const [inviteOpen, inviteHandlers] = useDisclosure(false);
  const [shootOpen, shootHandlers] = useDisclosure(false);
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [funnelRows, setFunnelRows] = useState<TeamFunnelRow[]>([]);
  const [funnelFrom, setFunnelFrom] = useState('');
  const [funnelTo, setFunnelTo] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<string | null>('photographer');
  const [limitOrders, setLimitOrders] = useState<number | string>(3);
  const [limitSpend, setLimitSpend] = useState<number | string>('');
  const [ttl, setTtl] = useState<string | null>('7');
  const [busy, setBusy] = useState(false);
  const [shootUrl, setShootUrl] = useState<string | null>(null);
  const [shootCategory, setShootCategory] = useState<string | null>('other');
  const [shootTier, setShootTier] = useState<string | null>('small');
  const [accessRows, setAccessRows] = useState<AccessRow[]>([]);
  const [memberSearchQ, setMemberSearchQ] = useState('');
  const [memberSearch, setMemberSearch] = useState('');
  const [memberRoleFilter, setMemberRoleFilter] = useState<string | null>(null);
  const [membersTotal, setMembersTotal] = useState(0);
  const [loadingMoreMembers, setLoadingMoreMembers] = useState(false);
  const [shootStats, setShootStats] = useState<{
    created: number;
    expired: number;
    success: number;
    active: number;
    conversion_rate: number;
  } | null>(null);

  const funnelParams = useCallback(() => {
    return {
      date_from: funnelFrom ? `${funnelFrom}T00:00:00Z` : undefined,
      date_to: funnelTo ? `${funnelTo}T23:59:59Z` : undefined,
    };
  }, [funnelFrom, funnelTo]);

  const memberParams = useCallback(
    (offset = 0) => {
      const params: Record<string, string | number> = { limit: MEMBER_PAGE, offset };
      if (memberSearch) params.search = memberSearch;
      if (memberRoleFilter) params.role = memberRoleFilter;
      return params;
    },
    [memberSearch, memberRoleFilter],
  );

  useEffect(() => {
    const t = setTimeout(() => setMemberSearch(memberSearchQ.trim()), 400);
    return () => clearTimeout(t);
  }, [memberSearchQ]);

  const load = useCallback(async () => {
    try {
      const [m, i, f, a, ss] = await Promise.all([
        api.get<{ items: Member[]; total?: number }>('/company/members', { params: memberParams(0) }),
        api.get<{ items: Invite[] }>('/company/invitations'),
        api.get<{ items: TeamFunnelRow[] }>('/company/publication-funnel', { params: funnelParams() }),
        api.get<{ items: AccessRow[] }>('/company/access-log').catch(() => ({ data: { items: [] as AccessRow[] } })),
        api
          .get<{
            created: number;
            expired: number;
            success: number;
            active: number;
            conversion_rate: number;
          }>('/company/shoot_links/stats')
          .catch(() => ({ data: null })),
      ]);
      setMembers(m.data.items ?? []);
      setMembersTotal(m.data.total ?? m.data.items?.length ?? 0);
      setInvites(i.data.items ?? []);
      setFunnelRows(f.data.items ?? []);
      setAccessRows(a.data.items ?? []);
      if (ss.data) setShootStats(ss.data);
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }, [funnelParams, memberParams]);

  async function loadMoreMembers() {
    if (loadingMoreMembers || members.length >= membersTotal) return;
    setLoadingMoreMembers(true);
    try {
      const { data } = await api.get<{ items: Member[]; total?: number }>('/company/members', {
        params: memberParams(members.length),
      });
      const next = data.items ?? [];
      setMembers((prev) => [...prev, ...next]);
      setMembersTotal(data.total ?? members.length + next.length);
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setLoadingMoreMembers(false);
    }
  }

  useEffect(() => {
    void load();
  }, [load]);

  async function sendInvite() {
    if (!email || !role) return;
    setBusy(true);
    try {
      const { data } = await api.post<{ url: string }>('/company/invite', {
        email,
        role,
        max_concurrent_orders: typeof limitOrders === 'number' ? limitOrders : Number(limitOrders) || 3,
        monthly_spending_limit:
          limitSpend === '' || limitSpend == null
            ? null
            : typeof limitSpend === 'number'
              ? limitSpend
              : Number(limitSpend),
        ttl_days: Number(ttl || 7),
      });
      notifications.show({ color: 'teal', message: `Приглашение создано: ${data.url}` });
      inviteHandlers.close();
      setEmail('');
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function createShootLink() {
    setBusy(true);
    try {
      const { data } = await api.post<{ url: string }>('/company/shoot_link', {
        category: shootCategory,
        tier: shootTier,
        ttl_hours: 48,
        max_uses: 1,
      });
      setShootUrl(data.url);
      notifications.show({ color: 'teal', message: 'Ссылка для фотографа создана' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <SellerShell>
      <PageHeader
        title="Команда и доступы"
        description="Приглашения, роли, лимиты и съёмка по ссылке для внештатных фотографов"
        action={
          <Group gap="sm">
            <Button variant="light" leftSection={<IconLink size={16} />} onClick={shootHandlers.open}>
              Ссылка на съёмку
            </Button>
            <Button leftSection={<IconUserPlus size={16} />} onClick={inviteHandlers.open}>
              Пригласить
            </Button>
          </Group>
        }
      />

      <SubNav
        items={[
          { href: '/team/roles', label: 'Роли' },
          { href: '/team/webhooks', label: 'Webhooks' },
          { href: '/team/policies', label: 'Политики' },
          { href: '/team/audit', label: 'Аудит' },
          { href: '/team/sessions', label: 'Сессии' },
          { href: '/team/api-keys', label: 'API-ключи' },
          { href: '/team/marketplace', label: 'Marketplace API' },
        ]}
      />

      <Surface mb="md">
        <Group justify="space-between" mb="sm" wrap="wrap">
          <Text fw={600}>Воронка публикации §7.9</Text>
          <Group align="flex-end" wrap="wrap">
            <TextInput
              type="date"
              label="С"
              size="xs"
              value={funnelFrom}
              onChange={(e) => setFunnelFrom(e.currentTarget.value)}
            />
            <TextInput
              type="date"
              label="По"
              size="xs"
              value={funnelTo}
              onChange={(e) => setFunnelTo(e.currentTarget.value)}
            />
            <Button variant="light" size="xs" onClick={() => void load()}>
              Период
            </Button>
            <Button
              variant="light"
              size="xs"
              onClick={async () => {
                try {
                  const { data } = await api.get<Blob>('/company/publication-funnel', {
                    params: { export: true, ...funnelParams() },
                    responseType: 'blob',
                  });
                  const url = URL.createObjectURL(data);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = 'team-publication-funnel.csv';
                  a.click();
                  URL.revokeObjectURL(url);
                } catch (e) {
                  notifications.show({ color: 'red', message: apiMessage(e) });
                }
              }}
            >
              CSV
            </Button>
          </Group>
        </Group>
        <ScrollTable>
          <Table miw={640} verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Сотрудник</Table.Th>
                <Table.Th>Gen</Table.Th>
                <Table.Th>DL</Table.Th>
                <Table.Th>Links</Table.Th>
                <Table.Th>OK</Table.Th>
                <Table.Th>Дней→verify</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {funnelRows.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={6}>
                    <Text c="dimmed" size="sm">
                      Нет данных (нужны завершённые генерации)
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                funnelRows.map((r) => (
                  <Table.Tr key={r.user_id}>
                    <Table.Td>{r.full_name || r.email || r.user_id}</Table.Td>
                    <Table.Td>{r.funnel.generated}</Table.Td>
                    <Table.Td>{r.funnel.downloaded}</Table.Td>
                    <Table.Td>{r.funnel.links_added}</Table.Td>
                    <Table.Td>{r.funnel.verified}</Table.Td>
                    <Table.Td>{r.avg_days_to_verification ?? '—'}</Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </ScrollTable>
      </Surface>

      <Surface mb="md">
        <Group justify="space-between" mb="sm">
          <Text fw={600}>Access log §10.7.2 (скачивания моделей)</Text>
          <Button
            size="xs"
            variant="light"
            onClick={async () => {
              try {
                const { data } = await api.get('/company/access-log/export', { responseType: 'blob' });
                const url = URL.createObjectURL(data);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'company-access-log.csv';
                a.click();
                URL.revokeObjectURL(url);
              } catch (e) {
                notifications.show({ color: 'red', message: apiMessage(e) });
              }
            }}
          >
            Export CSV
          </Button>
        </Group>
        <ScrollTable>
          <Table miw={560} verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Время</Table.Th>
                <Table.Th>User</Table.Th>
                <Table.Th>Model</Table.Th>
                <Table.Th>Format</Table.Th>
                <Table.Th>IP</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {accessRows.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={5}>
                    <Text c="dimmed" size="sm">
                      Пока нет скачиваний
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                accessRows.slice(0, 50).map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>{r.timestamp ? new Date(r.timestamp).toLocaleString('ru-RU') : '—'}</Table.Td>
                    <Table.Td>{r.user_id}</Table.Td>
                    <Table.Td>{r.model_uuid.slice(0, 8)}…</Table.Td>
                    <Table.Td>{r.file_format ?? '—'}</Table.Td>
                    <Table.Td>{r.ip_address ?? '—'}</Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </ScrollTable>
      </Surface>

      <Surface>
        <FilterRow>
          <TextInput
            label="Поиск"
            placeholder="Имя или email"
            value={memberSearchQ}
            onChange={(e) => setMemberSearchQ(e.currentTarget.value)}
          />
          <Select
            label="Роль"
            placeholder="Все роли"
            data={['owner', 'manager', 'photographer', 'viewer']}
            clearable
            value={memberRoleFilter}
            onChange={setMemberRoleFilter}
          />
        </FilterRow>
        <ScrollTable>
          <Table miw={720} verticalSpacing="md">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Сотрудник</Table.Th>
                <Table.Th>Роль</Table.Th>
                <Table.Th>Email</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {members.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={3}>
                    <EmptyState
                      title="В команде пока никого нет"
                      hint="Отправьте приглашение — сотрудник получит ссылку на email"
                    />
                  </Table.Td>
                </Table.Tr>
              ) : (
                members.map((m) => (
                  <Table.Tr key={m.user_id}>
                    <Table.Td fw={600}>{m.full_name || `User #${m.user_id}`}</Table.Td>
                    <Table.Td>{m.role}</Table.Td>
                    <Table.Td>{m.email}</Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </ScrollTable>
        {membersTotal > members.length ? (
          <Group justify="center" mt="md">
            <Button variant="light" loading={loadingMoreMembers} onClick={() => void loadMoreMembers()}>
              Загрузить ещё ({members.length}/{membersTotal})
            </Button>
          </Group>
        ) : null}
      </Surface>

      <Surface>
        <Text fw={700} mb="md">
          Исходящие приглашения
        </Text>
        {invites.length === 0 ? (
          <EmptyState title="Приглашений нет" />
        ) : (
          <ScrollTable>
            <Table miw={640} verticalSpacing="md">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Email</Table.Th>
                  <Table.Th>Роль</Table.Th>
                  <Table.Th>Статус</Table.Th>
                  <Table.Th>Ссылка</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {invites.map((inv) => (
                  <Table.Tr key={inv.id}>
                    <Table.Td>{inv.email}</Table.Td>
                    <Table.Td>{inv.role}</Table.Td>
                    <Table.Td>{inv.status}</Table.Td>
                    <Table.Td>
                      <Group gap={6} wrap="nowrap">
                        <Text size="sm" lineClamp={1} maw={220}>
                          {inv.url}
                        </Text>
                        <CopyButton value={inv.url}>
                          {({ copied, copy }) => (
                            <Tooltip label={copied ? 'Скопировано' : 'Копировать'}>
                              <ActionIcon variant="light" onClick={copy}>
                                {copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
                              </ActionIcon>
                            </Tooltip>
                          )}
                        </CopyButton>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </ScrollTable>
        )}
      </Surface>

      <Modal opened={inviteOpen} onClose={inviteHandlers.close} title="Пригласить сотрудника" centered radius="lg" padding="lg">
        <Stack gap="md">
          <Text size="sm" c="#6d6c77">
            Owner сохраняет контроль над балансом. Сотрудник входит по ссылке.
          </Text>
          <TextInput label="Email" type="email" required size="md" value={email} onChange={(e) => setEmail(e.currentTarget.value)} />
          <Select
            label="Роль"
            data={[
              { value: 'manager', label: 'Manager' },
              { value: 'photographer', label: 'Photographer' },
              { value: 'viewer', label: 'Viewer' },
            ]}
            value={role}
            onChange={setRole}
            size="md"
          />
          <NumberInput label="Лимит активных заказов" min={1} value={limitOrders} onChange={setLimitOrders} size="md" />
          <NumberInput label="Лимит расходов в месяц, ₽" min={0} value={limitSpend} onChange={setLimitSpend} size="md" />
          <Select label="Срок" data={[{ value: '1', label: '1 день' }, { value: '7', label: '7 дней' }, { value: '30', label: '30 дней' }]} value={ttl} onChange={setTtl} size="md" />
          <Button fullWidth loading={busy} onClick={() => void sendInvite()}>
            Создать приглашение
          </Button>
        </Stack>
      </Modal>

      <Modal opened={shootOpen} onClose={shootHandlers.close} title="Ссылка на съёмку" centered radius="lg" padding="lg" size="lg">
        <Stack gap="md">
          <Text size="sm" c="#6d6c77">
            Внештатный фотограф загрузит 12 ракурсов без регистрации (§3 / §20).
          </Text>
          {shootStats && (
            <Text size="sm">
              Статистика: создано {shootStats.created} · активны {shootStats.active} · истекли{' '}
              {shootStats.expired} · успешные {shootStats.success} (
              {(shootStats.conversion_rate * 100).toFixed(0)}%)
            </Text>
          )}
          <Select
            label="Категория"
            value={shootCategory}
            onChange={setShootCategory}
            data={[
              { value: 'clothing', label: 'Одежда' },
              { value: 'shoes', label: 'Обувь' },
              { value: 'electronics', label: 'Электроника' },
              { value: 'other', label: 'Другое' },
            ]}
          />
          <Select
            label="Тариф"
            value={shootTier}
            onChange={setShootTier}
            data={[
              { value: 'small', label: 'Small' },
              { value: 'large', label: 'Large' },
            ]}
          />
          <Button loading={busy} onClick={() => void createShootLink()}>
            Сгенерировать ссылку
          </Button>
          {shootUrl && (
            <Textarea label="Ссылка" value={shootUrl} readOnly minRows={2} />
          )}
          {shootUrl && (
            <Stack align="center" gap={4}>
              <QRCodeCanvas value={shootUrl} size={180} includeMargin />
              <Text size="xs" c="#6d6c77">
                Наведите камеру телефона, чтобы открыть съёмку
              </Text>
            </Stack>
          )}
          {shootUrl && (
            <CopyButton value={shootUrl}>
              {({ copied, copy }) => (
                <Button variant="light" leftSection={copied ? <IconCheck size={16} /> : <IconCopy size={16} />} onClick={copy}>
                  {copied ? 'Скопировано' : 'Копировать'}
                </Button>
              )}
            </CopyButton>
          )}
        </Stack>
      </Modal>
    </SellerShell>
  );
}
