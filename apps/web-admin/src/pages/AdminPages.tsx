import { ActionIcon, Button, Card, Center, Code, Group, Loader, Modal, NumberInput, ScrollArea, Select, SimpleGrid, Slider, Stack, Tabs, Text, TextInput, Textarea } from '@mantine/core';
import { IconDownload, IconPlus, IconRefresh, IconTrash } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { HealthCard, MetricGrid, PageHeader, SaveButton, ShellTable, StateBadge } from '../components/Panel';
import { api, getApiError } from '../services/api';

export function WorkersPage() {
  const [items, setItems] = useState<Array<{
    id: string;
    status: string;
    gpu_name?: string | null;
    gpu_load?: number | null;
    weight: number;
    grace_period: number;
    trellis_version?: string | null;
    docker_image?: string | null;
    maintenance?: boolean;
  }>>([]);
  const [rollout, setRollout] = useState({
    target_version: '2',
    default_docker_image: '',
    mixed_versions: false,
    maintenance_count: 0,
    workers_by_version: {} as Record<string, number>,
  });
  const [targetVersion, setTargetVersion] = useState('2');
  const [defaultImage, setDefaultImage] = useState('');
  const [summary, setSummary] = useState({ online: 0, total: 0, queue_normal: 0, queue_high: 0 });
  const [cloud, setCloud] = useState<Array<{
    id: number;
    provider: string;
    instance_id: string;
    worker_id: string;
    gpu: string;
    status: string;
    rub_per_hour: number;
  }>>([]);
  const [rules, setRules] = useState<Array<{
    id: number;
    name: string;
    queue_threshold: number;
    launch_count: number;
    provider: string;
    gpu: string;
    idle_timeout_min: number;
    max_cloud_workers: number;
    is_active: boolean;
  }>>([]);
  const [costs, setCosts] = useState({
    today_rub: 0,
    month_rub: 0,
    burn_rub_per_hour: 0,
    running_instances: 0,
    budget_blocked: false,
    cloud_monthly_budget_rub: 0,
    cloud_daily_budget_rub: 0,
  });
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [provider, setProvider] = useState<string | null>('intelion');
  const [gpu, setGpu] = useState('rtx4090');
  const [count, setCount] = useState(1);
  const [busy, setBusy] = useState(false);

  async function load() {
    const [w, c, r, cost, tr] = await Promise.all([
      api.get<{ summary: typeof summary; items: typeof items }>('/admin/workers'),
      api.get<{ items: typeof cloud }>('/admin/cloud/instances'),
      api.get<{ items: typeof rules }>('/admin/cloud/autoscaling/rules'),
      api.get<typeof costs>('/admin/cloud/costs'),
      api.get<typeof rollout>('/admin/trellis/rollout'),
    ]);
    setSummary(w.data.summary);
    setItems(w.data.items ?? []);
    setCloud(c.data.items ?? []);
    setRules(r.data.items ?? []);
    setCosts(cost.data);
    setRollout(tr.data);
    setTargetVersion(tr.data.target_version ?? '2');
    setDefaultImage(tr.data.default_docker_image ?? '');
  }

  useEffect(() => {
    load().catch((e) => notifications.show({ color: 'red', message: getApiError(e) })).finally(() => setLoading(false));
  }, []);

  async function downloadDeploy(role: string) {
    try {
      const { data } = await api.get<Record<string, unknown>>('/admin/deploy/bundle', {
        params: { role },
      });
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `deploy_${role.replace('-', '_')}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  if (loading) return <Center py="xl"><Loader color="brand" /></Center>;

  return (
    <>
      <PageHeader
        title="Воркеры"
        description="GPU-очередь · Intelion/Immers create/start/stop · авто-масштаб"
        action={
          <Group>
            <Button variant="light" leftSection={<IconDownload size={16} />} onClick={() => void downloadDeploy('worker')}>
              Deploy JSON
            </Button>
            <Button variant="subtle" size="compact-sm" onClick={() => void downloadDeploy('cloud')}>
              Cloud env
            </Button>
            <Button leftSection={<IconPlus size={16} />} onClick={() => setCreateOpen(true)}>
              Облачный инстанс
            </Button>
            <Button leftSection={<IconRefresh size={16} />} onClick={() => load()}>
              Обновить
            </Button>
          </Group>
        }
      />
      <MetricGrid
        items={[
          { label: 'Онлайн', value: String(summary.online), hint: `из ${summary.total}`, color: 'teal' },
          { label: 'Очередь normal', value: String(summary.queue_normal) },
          { label: 'Очередь high', value: String(summary.queue_high) },
          { label: 'Burn ₽/ч', value: String(costs.burn_rub_per_hour), hint: `сегодня ${costs.today_rub} ₽ · месяц ${costs.month_rub} ₽`, color: costs.budget_blocked ? 'red' : undefined },
          ...(costs.budget_blocked
            ? [{ label: 'Cloud budget', value: 'STOP', color: 'red' as const }]
            : []),
        ]}
      />
      <Card withBorder mb="md">
        <Stack gap="sm">
          <Group justify="space-between">
            <Text fw={600}>TRELLIS rollout §18</Text>
            {rollout.mixed_versions && (
              <StateBadge value="mixed versions" color="orange" />
            )}
          </Group>
          <SimpleGrid cols={{ base: 1, md: 3 }}>
            <TextInput
              label="Target version"
              value={targetVersion}
              onChange={(e) => setTargetVersion(e.currentTarget.value)}
            />
            <TextInput
              label="Default docker image"
              value={defaultImage}
              onChange={(e) => setDefaultImage(e.currentTarget.value)}
            />
            <Text size="sm" c="dimmed" mt={28}>
              maintenance: {rollout.maintenance_count} ·{' '}
              {Object.entries(rollout.workers_by_version)
                .map(([v, n]) => `${v}:${n}`)
                .join(' · ') || 'нет версий'}
            </Text>
          </SimpleGrid>
          <Group>
            <Button
              size="xs"
              variant="light"
              onClick={async () => {
                try {
                  await api.put('/admin/trellis/rollout', {
                    target_version: targetVersion,
                    default_docker_image: defaultImage || null,
                  });
                  await load();
                } catch (e) {
                  notifications.show({ color: 'red', message: getApiError(e) });
                }
              }}
            >
              Сохранить rollout
            </Button>
          </Group>
        </Stack>
      </Card>
      <ShellTable
        headers={['Воркер', 'Статус', 'TRELLIS', 'GPU', 'Вес', 'Grace', 'Действия']}
        rows={
          items.length
            ? items.map((w) => [
                w.id,
                <Group key={`s-${w.id}`} gap={6}>
                  <StateBadge value={w.status} color={w.status === 'online' ? 'teal' : 'orange'} />
                  {w.maintenance && <StateBadge value="maint" color="orange" />}
                </Group>,
                `${w.trellis_version ?? '—'}${w.docker_image ? ` · ${w.docker_image}` : ''}`,
                `${w.gpu_name ?? '—'} · ${w.gpu_load != null ? `${Math.round(w.gpu_load)}%` : '—'}`,
                <Slider
                  key={`w-${w.id}`}
                  defaultValue={Math.round((w.weight + 1) * 50)}
                  label={(v) => `${((v / 50) - 1).toFixed(1)}`}
                  w={120}
                  onChangeEnd={async (v) => {
                    const weight = Number(((v / 50) - 1).toFixed(2));
                    try {
                      await api.patch(`/admin/workers/${w.id}/weight`, null, { params: { weight } });
                      await load();
                    } catch (e) {
                      notifications.show({ color: 'red', message: getApiError(e) });
                    }
                  }}
                />,
                `${w.grace_period}с`,
                <Group key={`g-${w.id}`} gap={4}>
                  <Button
                    size="xs"
                    variant="light"
                    onClick={async () => {
                      try {
                        await api.patch(`/admin/workers/${w.id}/grace_period`, { grace_period: 30 });
                        await load();
                      } catch (e) {
                        notifications.show({ color: 'red', message: getApiError(e) });
                      }
                    }}
                  >
                    Grace 30
                  </Button>
                  <Button
                    size="xs"
                    variant="light"
                    color={w.maintenance ? 'teal' : 'orange'}
                    onClick={async () => {
                      try {
                        await api.post(`/admin/workers/${w.id}/maintenance`, {
                          enabled: !w.maintenance,
                        });
                        await load();
                      } catch (e) {
                        notifications.show({ color: 'red', message: getApiError(e) });
                      }
                    }}
                  >
                    {w.maintenance ? 'Maint OFF' : 'Maint ON'}
                  </Button>
                  <Button
                    size="xs"
                    variant="light"
                    onClick={async () => {
                      const ver = window.prompt('Rollout version', rollout.target_version || '2');
                      if (!ver) return;
                      try {
                        await api.post(`/admin/workers/${w.id}/trellis/rollout`, {
                          trellis_version: ver,
                          docker_image: defaultImage || undefined,
                        });
                        notifications.show({ color: 'teal', message: 'Rollout queued (maintenance ON)' });
                        await load();
                      } catch (e) {
                        notifications.show({ color: 'red', message: getApiError(e) });
                      }
                    }}
                  >
                    Rollout
                  </Button>
                  <Button
                    size="xs"
                    color="orange"
                    variant="light"
                    onClick={async () => {
                      const ver = window.prompt('Rollback version', '1');
                      if (!ver) return;
                      try {
                        await api.post(`/admin/workers/${w.id}/trellis/rollback`, {
                          trellis_version: ver,
                        });
                        notifications.show({ color: 'orange', message: 'Rollback pinned' });
                        await load();
                      } catch (e) {
                        notifications.show({ color: 'red', message: getApiError(e) });
                      }
                    }}
                  >
                    Rollback
                  </Button>
                  <Button
                    size="xs"
                    variant="subtle"
                    onClick={async () => {
                      try {
                        await api.post(`/admin/workers/${w.id}/trellis/complete`);
                        await load();
                      } catch (e) {
                        notifications.show({ color: 'red', message: getApiError(e) });
                      }
                    }}
                  >
                    Complete
                  </Button>
                </Group>,
              ])
            : [['—', 'Нет воркеров', '—', 'Heartbeat ещё не приходил', '—', '—', '—']]
        }
      />

      <PageHeader title="Облачные инстансы" description={`Месяц: ${costs.month_rub} ₽ · running: ${costs.running_instances}`} />
      <ShellTable
        headers={['Провайдер', 'Instance', 'Worker', 'GPU', 'Статус', '₽/ч', '']}
        rows={
          cloud.length
            ? cloud.map((c) => [
                c.provider,
                c.instance_id,
                c.worker_id,
                c.gpu,
                <StateBadge key={`cs-${c.id}`} value={c.status} />,
                String(c.rub_per_hour),
                <Group key={`ca-${c.id}`} gap={4}>
                  <Button
                    size="xs"
                    variant="light"
                    loading={busy}
                    onClick={async () => {
                      setBusy(true);
                      try {
                        await api.post(`/admin/cloud/instances/${c.instance_id}/start`);
                        await load();
                      } catch (e) {
                        notifications.show({ color: 'red', message: getApiError(e) });
                      } finally {
                        setBusy(false);
                      }
                    }}
                  >
                    Start
                  </Button>
                  <Button
                    size="xs"
                    color="orange"
                    variant="light"
                    loading={busy}
                    onClick={async () => {
                      setBusy(true);
                      try {
                        await api.post(`/admin/cloud/instances/${c.instance_id}/stop`);
                        await load();
                      } catch (e) {
                        notifications.show({ color: 'red', message: getApiError(e) });
                      } finally {
                        setBusy(false);
                      }
                    }}
                  >
                    Stop
                  </Button>
                </Group>,
              ])
            : [['—', 'Нет облачных инстансов', '—', '—', '—', '—', '—']]
        }
      />

      <PageHeader
        title="Авто-масштаб"
        description="Celery каждые 30с · queue_threshold → create · idle → stop"
        action={
          <Button
            size="sm"
            variant="light"
            onClick={async () => {
              try {
                const { data } = await api.post('/admin/cloud/autoscaling/run');
                notifications.show({ color: 'teal', message: JSON.stringify(data) });
                await load();
              } catch (e) {
                notifications.show({ color: 'red', message: getApiError(e) });
              }
            }}
          >
            Run once
          </Button>
        }
      />
      <ShellTable
        headers={['Имя', 'Порог Q', 'Launch', 'Провайдер', 'GPU', 'Idle мин', 'Max', 'Active']}
        rows={
          rules.length
            ? rules.map((r) => [
                r.name,
                String(r.queue_threshold),
                String(r.launch_count),
                r.provider,
                r.gpu,
                String(r.idle_timeout_min),
                String(r.max_cloud_workers),
                r.is_active ? 'да' : 'нет',
              ])
            : [['—', 'Правил нет — создайте через PUT /admin/cloud/autoscaling/rules', '—', '—', '—', '—', '—', '—']]
        }
      />

      <Modal opened={createOpen} onClose={() => setCreateOpen(false)} title="Создать облачный воркер" centered>
        <Stack>
          <Select
            label="Провайдер"
            data={[
              { value: 'intelion', label: 'Intelion Cloud' },
              { value: 'immers', label: 'Immers Cloud' },
            ]}
            value={provider}
            onChange={setProvider}
          />
          <TextInput label="GPU" value={gpu} onChange={(e) => setGpu(e.currentTarget.value)} />
          <NumberInput label="Количество" value={count} onChange={(v) => setCount(Number(v) || 1)} min={1} max={10} />
          <Button
            loading={busy}
            onClick={async () => {
              if (!provider) return;
              setBusy(true);
              try {
                await api.post('/admin/cloud/instances', { provider, gpu, count });
                notifications.show({ color: 'teal', message: 'Инстанс создан' });
                setCreateOpen(false);
                await load();
              } catch (e) {
                notifications.show({ color: 'red', message: getApiError(e) });
              } finally {
                setBusy(false);
              }
            }}
          >
            Запустить
          </Button>
        </Stack>
      </Modal>
    </>
  );
}

export function UsersPage() {
  const [items, setItems] = useState<Array<{ id: number; email: string; full_name?: string | null; status: string }>>([]);
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<{ items: typeof items }>('/admin/users')
      .then(({ data }) => setItems(data.items ?? []))
      .catch((e) => notifications.show({ color: 'red', message: getApiError(e) }))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Center py="xl"><Loader color="brand" /></Center>;
  const filtered = items.filter((u) => !q || `${u.id} ${u.email} ${u.full_name ?? ''}`.toLowerCase().includes(q.toLowerCase()));

  return (
    <>
      <PageHeader title="Пользователи" description="Селлеры, статусы учётных записей и право на забвение" />
      <Group mb="md">
        <TextInput placeholder="Поиск по ID, email" value={q} onChange={(e) => setQ(e.currentTarget.value)} />
      </Group>
      <ShellTable
        headers={['ID', 'Пользователь', 'Email', 'Статус', '']}
        rows={filtered.map((user) => [
          String(user.id),
          user.full_name || '—',
          user.email,
          <StateBadge key={user.id} value={user.status} color={user.status?.includes('active') ? 'teal' : 'orange'} />,
          <Button key={`b-${user.id}`} component={Link} to={`/users/${user.id}`} size="xs" variant="subtle">
            Карточка
          </Button>,
        ])}
      />
    </>
  );
}

export function UserDetailPage() {
  const { id } = useParams();
  const [user, setUser] = useState<{
    id: number;
    email: string;
    full_name?: string | null;
    status: string;
    balance: number;
    orders_count: number;
    created_at?: string | null;
    orders: Array<{ id: number; status: string; amount: number; created_at?: string | null }>;
  } | null>(null);

  async function load() {
    const { data } = await api.get(`/admin/users/${id}`);
    setUser(data);
  }

  useEffect(() => {
    load().catch((e) => notifications.show({ color: 'red', message: getApiError(e) }));
  }, [id]);

  if (!user) return <Center py="xl"><Loader color="brand" /></Center>;

  return (
    <>
      <PageHeader title={`Пользователь ${user.id}`} description="Профиль, заказы, баланс и действия с данными" />
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <Card withBorder>
          <Stack>
            <Text fw={600}>{user.full_name || 'Без имени'}</Text>
            <Text size="sm">
              {user.email} · {user.created_at ? new Date(user.created_at).toLocaleDateString('ru-RU') : '—'}
            </Text>
            <StateBadge value={user.status} color={user.status?.includes('active') ? 'teal' : 'orange'} />
            <Group>
              <Button
                color="orange"
                variant="light"
                onClick={async () => {
                  await api.post(`/admin/users/${user.id}/block`, { blocked: user.status !== 'blocked' });
                  await load();
                }}
              >
                {user.status === 'blocked' ? 'Разблокировать' : 'Заблокировать'}
              </Button>
              <Button
                color="red"
                variant="light"
                leftSection={<IconTrash size={16} />}
                onClick={async () => {
                  if (!confirm('Удалить пользователя (право на забвение)?')) return;
                  await api.post(`/admin/users/${user.id}/delete`);
                  await load();
                }}
              >
                Удалить данные
              </Button>
            </Group>
          </Stack>
        </Card>
        <Card withBorder>
          <Text fw={600} mb="sm">Активность</Text>
          <MetricGrid
            items={[
              { label: 'Заказов', value: String(user.orders_count) },
              { label: 'Баланс', value: `${user.balance.toLocaleString('ru-RU')} ₽` },
            ]}
          />
        </Card>
      </SimpleGrid>
      <ShellTable
        headers={['Заказ', 'Статус', 'Дата', 'Сумма']}
        rows={user.orders.map((o) => [
          String(o.id),
          <StateBadge key={o.id} value={o.status} color="teal" />,
          o.created_at ? new Date(o.created_at).toLocaleString('ru-RU') : '—',
          `${o.amount} ₽`,
        ])}
      />
    </>
  );
}

export function CompaniesPage() {
  const [items, setItems] = useState<Array<{ id: number; name: string; members_count: number; balance: number; status: string }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<{ items: typeof items }>('/admin/companies')
      .then(({ data }) => setItems(data.items ?? []))
      .catch((e) => notifications.show({ color: 'red', message: getApiError(e) }))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Center py="xl"><Loader color="brand" /></Center>;

  return (
    <>
      <PageHeader title="B2B-клиенты" description="Компании, лимиты, персональные цены и API-ключи" />
      <ShellTable
        headers={['ID', 'Компания', 'Сотрудники', 'Баланс', 'Статус', '']}
        rows={items.map((c) => [
          String(c.id),
          c.name,
          String(c.members_count),
          `${c.balance.toLocaleString('ru-RU')} ₽`,
          <StateBadge key={c.id} value={c.status} color={c.status === 'active' ? 'teal' : 'red'} />,
          <Button key={`o-${c.id}`} component={Link} to={`/companies/${c.id}`} size="xs" variant="subtle">
            Открыть
          </Button>,
        ])}
      />
    </>
  );
}

type CompanyMemberRow = {
  user_id: number;
  role: string;
  max_concurrent_orders?: number | null;
  monthly_spending_limit?: number | null;
};
type ApiKeyRow = {
  id: number;
  name: string;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
  last_used_at: string | null;
  created_at: string | null;
};
type PriceOverride = { type: 'fixed' | 'percent'; value: number };
type PriceData = {
  base: Record<string, number>;
  overrides: Record<string, PriceOverride>;
  effective: Record<string, number>;
};

const PRICE_TIERS: Array<{ code: string; label: string }> = [
  { code: 'small', label: 'Малый' },
  { code: 'large', label: 'Крупный' },
  { code: 'import_glb', label: 'Импорт GLB' },
];

export function CompanyDetailPage() {
  const { id } = useParams();
  const [company, setCompany] = useState<{
    id: number;
    name: string;
    inn: string;
    balance: number;
    status: string;
    settings?: { force_trellis_version?: string | null };
    members: CompanyMemberRow[];
  } | null>(null);
  const [forceTrellis, setForceTrellis] = useState('');
  const [stats, setStats] = useState({
    orders: 0,
    revenue: 0,
    shoot_links: { created: 0, expired: 0, success: 0, active: 0, conversion_rate: 0 },
  });
  const [shootRecent, setShootRecent] = useState<
    Array<{ id: number; token: string; status: string; used_count: number; created_at?: string }>
  >([]);
  const [apiKeys, setApiKeys] = useState<ApiKeyRow[]>([]);
  const [invites, setInvites] = useState<Invitation[]>([]);
  const [logs, setLogs] = useState<
    Array<{ id: number; action: string; user_id: number | null; created_at: string | null }>
  >([]);
  const [prices, setPrices] = useState<PriceData | null>(null);
  const [priceDraft, setPriceDraft] = useState<Record<string, PriceOverride>>({});
  const [editMember, setEditMember] = useState<CompanyMemberRow | null>(null);
  const [limitDraft, setLimitDraft] = useState<{ mco: number | ''; msl: number | '' }>({ mco: '', msl: '' });

  async function load() {
    const [c, s, sl, keys, inv, lg, pr] = await Promise.all([
      api.get(`/admin/companies/${id}`),
      api.get(`/admin/companies/${id}/stats`),
      api.get(`/admin/companies/${id}/shoot-links`),
      api.get(`/admin/companies/${id}/api-keys`),
      api.get(`/admin/companies/${id}/invitations`),
      api.get(`/admin/companies/${id}/logs`),
      api.get(`/admin/companies/${id}/price-overrides`),
    ]);
    setCompany(c.data);
    setForceTrellis(c.data.settings?.force_trellis_version ?? '');
    setStats({
      orders: s.data.orders ?? 0,
      revenue: s.data.revenue ?? 0,
      shoot_links: s.data.shoot_links ?? {
        created: 0,
        expired: 0,
        success: 0,
        active: 0,
        conversion_rate: 0,
      },
    });
    setShootRecent(sl.data.recent ?? []);
    setApiKeys(keys.data.items ?? []);
    setInvites(inv.data.items ?? []);
    setLogs(lg.data.items ?? []);
    setPrices(pr.data);
    setPriceDraft(pr.data.overrides ?? {});
  }

  useEffect(() => {
    load().catch((e) => notifications.show({ color: 'red', message: getApiError(e) }));
  }, [id]);

  async function savePrices() {
    try {
      await api.put(`/admin/companies/${company!.id}/price-overrides`, {
        price_overrides: priceDraft,
      });
      notifications.show({ color: 'teal', message: 'Индивидуальные цены сохранены' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  async function revokeKey(keyId: number) {
    if (!confirm('Отозвать API-ключ?')) return;
    try {
      await api.post(`/admin/companies/${company!.id}/api-keys/${keyId}/revoke`);
      notifications.show({ color: 'teal', message: 'Ключ отозван' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  async function revokeInvite(inviteId: number) {
    if (!confirm('Отозвать приглашение?')) return;
    try {
      await api.post(`/admin/invitations/${inviteId}/revoke`);
      notifications.show({ color: 'teal', message: 'Приглашение отозвано' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  async function saveMemberLimits() {
    if (!editMember) return;
    try {
      await api.patch(`/admin/companies/${company!.id}/members/${editMember.user_id}/limits`, {
        max_concurrent_orders: limitDraft.mco === '' ? null : limitDraft.mco,
        monthly_spending_limit: limitDraft.msl === '' ? null : limitDraft.msl,
      });
      notifications.show({ color: 'teal', message: 'Лимиты сохранены' });
      setEditMember(null);
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  if (!company) return <Center py="xl"><Loader color="brand" /></Center>;

  const sl = stats.shoot_links;

  return (
    <>
      <PageHeader title={company.name} description={`ИНН ${company.inn} · статус ${company.status}`} />
      <SimpleGrid cols={{ base: 1, md: 2 }} mb="md">
        <Card withBorder>
          <Stack>
            <Text fw={600}>Реквизиты</Text>
            <Text size="sm">Баланс: {company.balance.toLocaleString('ru-RU')} ₽</Text>
            <TextInput
              label="Force TRELLIS version (§18.4.2)"
              placeholder="default / 1 / 2"
              value={forceTrellis}
              onChange={(e) => setForceTrellis(e.currentTarget.value)}
            />
            <Button
              variant="light"
              onClick={async () => {
                try {
                  await api.patch(`/admin/companies/${company.id}/settings`, {
                    force_trellis_version: forceTrellis.trim() || 'default',
                  });
                  notifications.show({ color: 'teal', message: 'Версия TRELLIS сохранена' });
                  await load();
                } catch (e) {
                  notifications.show({ color: 'red', message: getApiError(e) });
                }
              }}
            >
              Сохранить TRELLIS pin
            </Button>
            <Text size="sm">
              Заказов: {stats.orders} · Выручка: {stats.revenue.toLocaleString('ru-RU')} ₽
            </Text>
            <Button
              color="orange"
              variant="light"
              onClick={async () => {
                await api.post(`/admin/companies/${company.id}/block`);
                await load();
              }}
            >
              {company.status === 'blocked' ? 'Разблокировать' : 'Заблокировать'}
            </Button>
          </Stack>
        </Card>
        <Card withBorder>
          <Text fw={600} mb="sm">Сотрудники и лимиты (§11.6)</Text>
          <ShellTable
            headers={['User ID', 'Роль', 'Заказов', 'Лимит ₽/мес', '']}
            rows={company.members.map((m) => [
              String(m.user_id),
              m.role,
              m.max_concurrent_orders != null ? String(m.max_concurrent_orders) : '∞',
              m.monthly_spending_limit != null ? m.monthly_spending_limit.toLocaleString('ru-RU') : '∞',
              <Button
                key={`ml${m.user_id}`}
                size="xs"
                variant="light"
                onClick={() => {
                  setEditMember(m);
                  setLimitDraft({
                    mco: m.max_concurrent_orders ?? '',
                    msl: m.monthly_spending_limit ?? '',
                  });
                }}
              >
                Лимиты
              </Button>,
            ])}
          />
        </Card>
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, md: 2 }} mb="md">
        <Card withBorder>
          <Text fw={600} mb="sm">Индивидуальные цены (§11.4)</Text>
          <Stack gap="xs">
            {PRICE_TIERS.map((t) => {
              const ov = priceDraft[t.code];
              return (
                <Group key={t.code} align="flex-end" gap="xs" wrap="nowrap">
                  <Text size="sm" w={90}>{t.label}</Text>
                  <Text size="xs" c="dimmed" w={70}>
                    база {prices?.base?.[t.code] ?? '—'}₽
                  </Text>
                  <Select
                    w={110}
                    value={ov?.type ?? ''}
                    placeholder="нет"
                    data={[
                      { value: '', label: 'Нет' },
                      { value: 'fixed', label: 'Фикс ₽' },
                      { value: 'percent', label: 'Скидка %' },
                    ]}
                    onChange={(v) =>
                      setPriceDraft((d) => {
                        const next = { ...d };
                        if (!v) delete next[t.code];
                        else next[t.code] = { type: v as 'fixed' | 'percent', value: ov?.value ?? 0 };
                        return next;
                      })
                    }
                  />
                  <NumberInput
                    w={110}
                    disabled={!ov}
                    value={ov?.value ?? ''}
                    min={0}
                    max={ov?.type === 'percent' ? 100 : undefined}
                    onChange={(v) =>
                      setPriceDraft((d) => ({
                        ...d,
                        [t.code]: { type: ov?.type ?? 'fixed', value: Number(v) || 0 },
                      }))
                    }
                  />
                </Group>
              );
            })}
            <Button variant="light" onClick={savePrices} mt="xs">Сохранить цены</Button>
          </Stack>
        </Card>
        <Card withBorder>
          <Text fw={600} mb="sm">API-ключи (§8.8)</Text>
          <ShellTable
            headers={['Название', 'Prefix', 'Активен', '']}
            rows={
              apiKeys.length
                ? apiKeys.map((k) => [
                    k.name,
                    <Code key={`c${k.id}`}>{k.key_prefix}</Code>,
                    <StateBadge key={`a${k.id}`} value={k.is_active ? 'да' : 'нет'} color={k.is_active ? 'teal' : 'red'} />,
                    k.is_active ? (
                      <ActionIcon key={`rk${k.id}`} color="red" variant="light" onClick={() => revokeKey(k.id)}>
                        <IconTrash size={16} />
                      </ActionIcon>
                    ) : (
                      <span key={`e${k.id}`}>—</span>
                    ),
                  ])
                : [['—', 'Нет ключей', '—', '—']]
            }
          />
        </Card>
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, md: 2 }} mb="md">
        <Card withBorder>
          <Text fw={600} mb="sm">Приглашения (§11.6)</Text>
          <ShellTable
            headers={['Email', 'Роль', 'Статус', '']}
            rows={
              invites.length
                ? invites.map((inv) => [
                    inv.email,
                    inv.role,
                    <StateBadge
                      key={`is${inv.id}`}
                      value={inv.status}
                      color={inv.status === 'pending' ? 'brand' : inv.status === 'accepted' ? 'teal' : 'red'}
                    />,
                    inv.status === 'pending' ? (
                      <ActionIcon key={`ri${inv.id}`} color="red" variant="light" onClick={() => revokeInvite(inv.id)}>
                        <IconTrash size={16} />
                      </ActionIcon>
                    ) : (
                      <span key={`ei${inv.id}`}>—</span>
                    ),
                  ])
                : [['—', '—', 'Нет приглашений', '—']]
            }
          />
        </Card>
        <Card withBorder>
          <Text fw={600} mb="sm">Аудит (§10.7.7)</Text>
          <ShellTable
            headers={['Действие', 'User', 'Когда']}
            rows={
              logs.length
                ? logs.slice(0, 20).map((r) => [
                    r.action,
                    r.user_id != null ? String(r.user_id) : '—',
                    r.created_at?.slice(0, 19) ?? '—',
                  ])
                : [['Нет событий', '—', '—']]
            }
          />
        </Card>
      </SimpleGrid>

      <Modal opened={!!editMember} onClose={() => setEditMember(null)} title={`Лимиты сотрудника #${editMember?.user_id ?? ''}`}>
        <Stack>
          <NumberInput
            label="Макс. одновременных заказов"
            placeholder="без лимита"
            min={0}
            value={limitDraft.mco}
            onChange={(v) => setLimitDraft((d) => ({ ...d, mco: v === '' ? '' : Number(v) }))}
          />
          <NumberInput
            label="Месячный лимит трат, ₽"
            placeholder="без лимита"
            min={0}
            value={limitDraft.msl}
            onChange={(v) => setLimitDraft((d) => ({ ...d, msl: v === '' ? '' : Number(v) }))}
          />
          <Button onClick={saveMemberLimits}>Сохранить</Button>
        </Stack>
      </Modal>
      <PageHeader title="Shoot-links (§3.15.4)" description="Созданные / истёкшие / успешные съёмки" />
      <MetricGrid
        items={[
          { label: 'Создано', value: String(sl.created ?? 0) },
          { label: 'Активны', value: String(sl.active ?? 0) },
          { label: 'Истекли', value: String(sl.expired ?? 0) },
          { label: 'Успешные', value: String(sl.success ?? 0), color: 'teal' },
          {
            label: 'Conversion',
            value: `${((sl.conversion_rate ?? 0) * 100).toFixed(1)}%`,
          },
        ]}
      />
      <ShellTable
        headers={['ID', 'Token', 'Статус', 'Uses', 'Создана']}
        rows={
          shootRecent.length
            ? shootRecent.map((r) => [
                String(r.id),
                r.token,
                <StateBadge key={`s${r.id}`} value={r.status} />,
                String(r.used_count),
                r.created_at?.slice(0, 19) ?? '—',
              ])
            : [['—', 'Нет ссылок', '—', '—', '—']]
        }
      />
    </>
  );
}

type Invitation = {
  id: number;
  email: string;
  company_id: number | null;
  company_name: string | null;
  role: string;
  status: string;
  expires_at: string | null;
  created_at: string | null;
};

export function InvitationsPage() {
  const [items, setItems] = useState<Invitation[]>([]);
  const [status, setStatus] = useState<string>('pending');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<{ items: Invitation[] }>('/admin/invitations', {
        params: { status },
      });
      setItems(data.items ?? []);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => {
    load();
  }, [load]);

  async function revoke(id: number) {
    if (!confirm('Отозвать приглашение?')) return;
    try {
      await api.post(`/admin/invitations/${id}/revoke`);
      notifications.show({ color: 'teal', message: 'Приглашение отозвано' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  return (
    <>
      <PageHeader
        title="Приглашения"
        description="Активные приглашения сотрудников в B2B-компании (§11.6)"
        action={
          <Select
            value={status}
            onChange={(v) => setStatus(v || 'pending')}
            data={[
              { value: 'pending', label: 'Активные' },
              { value: 'accepted', label: 'Принятые' },
              { value: 'revoked', label: 'Отозванные' },
              { value: 'all', label: 'Все' },
            ]}
            w={180}
          />
        }
      />
      {loading ? (
        <Center py="xl"><Loader color="brand" /></Center>
      ) : (
        <ShellTable
          headers={['Email', 'Компания', 'Роль', 'Статус', 'Срок', '']}
          rows={
            items.length
              ? items.map((inv) => [
                  inv.email,
                  inv.company_name || (inv.company_id ? `#${inv.company_id}` : '—'),
                  inv.role,
                  <StateBadge
                    key={`s${inv.id}`}
                    value={inv.status}
                    color={inv.status === 'pending' ? 'brand' : inv.status === 'accepted' ? 'teal' : 'red'}
                  />,
                  inv.expires_at ? new Date(inv.expires_at).toLocaleDateString('ru-RU') : '—',
                  inv.status === 'pending' ? (
                    <ActionIcon key={`r${inv.id}`} color="red" variant="light" onClick={() => revoke(inv.id)}>
                      <IconTrash size={16} />
                    </ActionIcon>
                  ) : (
                    <span key={`e${inv.id}`}>—</span>
                  ),
                ])
              : [['—', 'Нет приглашений', '—', '—', '—', '—']]
          }
        />
      )}
    </>
  );
}

export function PromocodesPage() {
  const [opened, setOpened] = useState(false);
  return (
    <>
      <PageHeader
        title="Промокоды"
        description="Скидки, лимиты активаций и статистика использования"
        action={
          <Button leftSection={<IconPlus size={16} />} onClick={() => setOpened(true)}>
            Создать
          </Button>
        }
      />
      <ShellTable
        headers={['Код', 'Скидка', 'Использовано', 'Действует до', 'Статус']}
        rows={[[<Text key="c" fw={600}>SUMMER26</Text>, '15%', '42 / 100', '31.08.2026', <StateBadge key="s" value="Активен" color="teal" />]]}
      />
      <Modal opened={opened} onClose={() => setOpened(false)} title="Новый промокод">
        <Stack>
          <TextInput label="Код" placeholder="SUMMER26" />
          <NumberInput label="Скидка, %" min={1} max={100} />
          <NumberInput label="Лимит активаций" />
          <Button onClick={() => setOpened(false)}>Создать</Button>
        </Stack>
      </Modal>
    </>
  );
}

export function CampaignsPage() {
  return (
    <>
      <PageHeader title="Кампании" description="Маркетинговые кампании, сегменты и ROI" />
      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <Card withBorder>
          <Stack>
            <TextInput label="Название кампании" />
            <Select label="Сегмент" data={['Новые пользователи', 'Неактивные 30 дней', 'B2B']} />
            <Textarea label="Сообщение" minRows={4} />
            <Group>
              <Button>Запустить кампанию</Button>
              <Button variant="light">Сохранить черновик</Button>
            </Group>
          </Stack>
        </Card>
        <Card withBorder>
          <Text fw={600}>Результаты кампаний</Text>
          <MetricGrid items={[{ label: 'Охват', value: '—' }, { label: 'Конверсия', value: '—' }, { label: 'ROI', value: '—' }]} />
        </Card>
      </SimpleGrid>
    </>
  );
}

export function PushPage() {
  return (
    <>
      <PageHeader title="Push-рассылки" description="Массовые уведомления" />
      <Card withBorder>
        <Stack>
          <Select label="Получатели" data={['Все активные']} defaultValue="Все активные" />
          <TextInput label="Заголовок" />
          <Textarea label="Текст уведомления" minRows={3} />
          <Button w="fit-content">Отправить на модерацию</Button>
        </Stack>
      </Card>
    </>
  );
}

export function ModerationPage() {
  return (
    <>
      <PageHeader title="Модерация" description="NSFW-проверка" />
      <ShellTable
        headers={['Материал', 'Пользователь', 'Оценка', 'Действие']}
        rows={[['—', 'Нет в очереди', '—', '—']]}
      />
    </>
  );
}

export function TaxPage() {
  return (
    <>
      <PageHeader title="Налоговый модуль" description="Реквизиты и выгрузка" />
      <Card withBorder>
        <Stack>
          <TextInput label="Наименование / ФИО" />
          <TextInput label="ИНН" />
          <SaveButton>Сохранить реквизиты</SaveButton>
        </Stack>
      </Card>
    </>
  );
}

export function LegalPage() {
  const [docs, setDocs] = useState<Array<{ slug: string; title: string; version: number }>>([]);
  const [consents, setConsents] = useState<
    Array<{ email?: string; document_slug: string; document_version: number; created_at?: string }>
  >([]);
  const [slug, setSlug] = useState('terms');
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [saving, setSaving] = useState(false);

  async function load() {
    const [d, c] = await Promise.all([api.get('/legal'), api.get('/admin/legal/consents')]);
    setDocs(d.data.items ?? []);
    setConsents(c.data.items ?? []);
  }

  useEffect(() => {
    load().catch((e) => notifications.show({ color: 'red', message: getApiError(e) }));
  }, []);

  useEffect(() => {
    if (!slug) return;
    api
      .get(`/legal/${slug}`)
      .then(({ data }) => {
        setTitle(data.title);
        setBody(data.body);
      })
      .catch(() => undefined);
  }, [slug]);

  return (
    <>
      <PageHeader title="Юридические документы" description="Версии документов и согласия" />
      <Tabs defaultValue="documents">
        <Tabs.List>
          <Tabs.Tab value="documents">Документы</Tabs.Tab>
          <Tabs.Tab value="consents">Согласия</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="documents" pt="md">
          <Card withBorder>
            <Stack>
              <Select
                label="Документ"
                data={docs.map((d) => ({ value: d.slug, label: `${d.title} (v${d.version})` }))}
                value={slug}
                onChange={(v) => setSlug(v || 'terms')}
              />
              <TextInput label="Название" value={title} onChange={(e) => setTitle(e.currentTarget.value)} />
              <Textarea label="Текст" minRows={8} value={body} onChange={(e) => setBody(e.currentTarget.value)} />
              <Button
                loading={saving}
                onClick={async () => {
                  setSaving(true);
                  try {
                    await api.post(`/legal/admin/${slug}/publish`, { title, body });
                    await load();
                    notifications.show({ color: 'green', message: 'Новая версия опубликована' });
                  } catch (e) {
                    notifications.show({ color: 'red', message: getApiError(e) });
                  } finally {
                    setSaving(false);
                  }
                }}
              >
                Опубликовать версию
              </Button>
            </Stack>
          </Card>
        </Tabs.Panel>
        <Tabs.Panel value="consents" pt="md">
          <ShellTable
            headers={['Пользователь', 'Документ', 'Версия', 'Дата']}
            rows={consents.map((c) => [
              c.email ?? '—',
              c.document_slug,
              String(c.document_version),
              c.created_at ? new Date(c.created_at).toLocaleString('ru-RU') : '—',
            ])}
          />
        </Tabs.Panel>
      </Tabs>
    </>
  );
}

export function SettingsPage() {
  return (
    <>
      <PageHeader title="Настройки" description="Тарифы и оповещения" />
      <Card withBorder>
        <SimpleGrid cols={{ base: 1, sm: 3 }}>
          <NumberInput label="Малый тариф, ₽" defaultValue={2990} />
          <NumberInput label="Крупный тариф, ₽" defaultValue={5990} />
          <NumberInput label="Grace period, сек." defaultValue={30} />
        </SimpleGrid>
        <Button mt="md">Сохранить</Button>
      </Card>
    </>
  );
}

export function StoragePage() {
  const [health, setHealth] = useState<{
    ok?: boolean;
    buckets?: string[];
    error?: string;
    total_bytes?: number;
    used_percent?: number | null;
    free_percent?: number | null;
    alert_disk_high?: boolean;
    alert_disk_critical?: boolean;
    alert_replication_failed?: boolean;
    usage?: Array<{ bucket: string; objects?: number; bytes?: number; error?: string }>;
    smart?: { status?: string; note?: string; source?: string };
    smart_disks?: Array<{
      device?: string;
      model?: string;
      health?: string;
      temp_c?: number;
      used_percent?: number;
      reallocated_sectors?: number;
      wear_percent?: number;
      remaining_life_percent?: number;
      error?: string;
    }>;
    cluster_ha?: {
      minio_replication?: Array<{
        bucket?: string;
        status?: string;
        pending?: number;
        pending_objects?: number;
        failed_minutes?: number;
        failed_since?: string;
      }>;
      postgres?: {
        role?: string;
        lag_bytes?: number;
        wal_state?: string;
        state?: string;
      };
      nodes?: Array<{ id?: string; name?: string; last_seen?: string; last_seen_age_sec?: number }>;
      source?: string | null;
    };
    encryption?: {
      mode?: string;
      kms_key_configured?: boolean;
      kms_key_id_masked?: string | null;
    };
  }>({});
  const [enc, setEnc] = useState<{
    mode?: string;
    kms_key_configured?: boolean;
    kms_key_id_masked?: string | null;
  }>({});
  const [lastCheck, setLastCheck] = useState<string>('');
  const [writeAct, setWriteAct] = useState<{
    under_load?: boolean;
    freeze_indicator?: boolean;
    stale_seconds?: number | null;
    last_write_at?: string | null;
    queued_tasks?: number;
    processing_tasks?: number;
    pg_tx_1h?: number;
  } | null>(null);
  const [logsOpen, setLogsOpen] = useState(false);
  const [logContainers, setLogContainers] = useState<string[]>([]);
  const [logContainer, setLogContainer] = useState<string | null>('postgres');
  const [logLines, setLogLines] = useState<
    Array<{ timestamp?: string; message?: string; level?: string }>
  >([]);
  const [logBackend, setLogBackend] = useState('');
  const [logsLoading, setLogsLoading] = useState(false);
  const [fioBusy, setFioBusy] = useState(false);
  const [timelineDays, setTimelineDays] = useState('7');
  const [timelineNodeId, setTimelineNodeId] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<{
    days?: number;
    nodes?: Array<{
      node_id: string;
      node_name?: string;
      uptime_percent?: number;
      offline_sec?: number;
      segments?: Array<{ status: string; started_at: string; ended_at?: string | null; duration_sec: number }>;
    }>;
  } | null>(null);
  const [forecast, setForecast] = useState<{
    current_used_percent?: number | null;
    growth_percent_per_day?: number | null;
    days_until_full?: number | null;
    forecast_alert?: boolean;
    wearout?: Array<{
      device?: string;
      wear_percent?: number;
      needs_replace?: boolean;
      bad_sectors?: boolean;
      reallocated_sectors?: number;
    }>;
    wearout_alert?: boolean;
  } | null>(null);

  async function check() {
    try {
      const { data } = await api.get('/storage/smart');
      setHealth(data);
      setEnc(data.encryption || {});
    } catch (e) {
      try {
        const { data } = await api.get('/storage/health');
        setHealth(data);
        setEnc(data.encryption || {});
      } catch (e2) {
        setHealth({ ok: false, error: getApiError(e2) });
      }
    }
    try {
      const { data } = await api.get('/storage/encryption');
      setEnc(data);
    } catch {
      /* optional */
    }
    try {
      const { data } = await api.get('/admin/write-activity');
      setWriteAct(data);
    } catch {
      /* optional */
    }
    try {
      const { data } = await api.get('/admin/storage/node-timeline', {
        params: {
          days: Number(timelineDays) || 7,
          ...(timelineNodeId ? { node_id: timelineNodeId } : {}),
        },
      });
      setTimeline(data);
    } catch {
      /* optional */
    }
    try {
      const { data } = await api.get('/admin/storage/disk-forecast', { params: { days: 14 } });
      setForecast(data);
    } catch {
      /* optional */
    }
  }

  useEffect(() => {
    check();
  }, []);

  const repl = health.cluster_ha?.minio_replication || [];
  const pg = health.cluster_ha?.postgres || {};
  const nodes = health.cluster_ha?.nodes || [];

  return (
    <>
      <PageHeader
        title="Кластер хранения"
        description="MinIO SMART / disk / replication / PG lag §11.16 / §12.4.1"
        action={
          <Group>
            <Button leftSection={<IconRefresh size={16} />} onClick={check}>
              Проверить
            </Button>
            <Button
              variant="light"
              onClick={async () => {
                try {
                  const { data } = await api.post('/storage/init');
                  notifications.show({ color: 'green', message: `Buckets: ${(data.buckets || []).join(', ')}` });
                  await check();
                } catch (e) {
                  notifications.show({ color: 'red', message: getApiError(e) });
                }
              }}
            >
              Init buckets
            </Button>
            <Button
              variant="light"
              onClick={async () => {
                try {
                  const { data } = await api.post('/storage/encryption/apply');
                  notifications.show({
                    color: 'teal',
                    message: `SSE: ${data.encryption?.mode ?? 'ok'}`,
                  });
                  await check();
                } catch (e) {
                  notifications.show({ color: 'red', message: getApiError(e) });
                }
              }}
            >
              Apply SSE
            </Button>
            <Button
              variant="light"
              onClick={async () => {
                try {
                  const { data } = await api.post<{
                    alerts_sent?: string[];
                    status?: string;
                    used_percent?: number;
                    free_percent?: number;
                    thresholds?: Record<string, number>;
                  }>('/admin/storage-alerts/check');
                  setLastCheck(
                    `sent=${(data.alerts_sent || []).join(',') || 'none'} · free ${data.free_percent ?? '—'}%`,
                  );
                  notifications.show({
                    color: 'teal',
                    message: `Cluster alerts: ${data.status} · used ${data.used_percent ?? '—'}% · ${(data.alerts_sent || []).join(',') || 'none'}`,
                  });
                  await check();
                } catch (e) {
                  notifications.show({ color: 'red', message: getApiError(e) });
                }
              }}
            >
              Check disk/SMART/repl→alerts
            </Button>
            <Button
              variant="light"
              color="orange"
              onClick={async () => {
                try {
                  const { data } = await api.post<{ mode?: string; result?: { ok?: boolean; error?: string } }>(
                    '/admin/storage/force-resync-minio',
                  );
                  notifications.show({
                    color: data.result?.ok !== false ? 'teal' : 'orange',
                    message: `Force Resync MinIO: ${data.mode} · ${data.result?.error || 'ok'}`,
                  });
                } catch (e) {
                  notifications.show({ color: 'red', message: getApiError(e) });
                }
              }}
            >
              Force Resync MinIO
            </Button>
            <Button
              variant="light"
              color="orange"
              onClick={async () => {
                try {
                  const { data } = await api.post<{ mode?: string; result?: { ok?: boolean; error?: string } }>(
                    '/admin/storage/restart-patroni-replication',
                  );
                  notifications.show({
                    color: data.result?.ok !== false ? 'teal' : 'orange',
                    message: `Restart Patroni: ${data.mode} · ${data.result?.error || 'ok'}`,
                  });
                } catch (e) {
                  notifications.show({ color: 'red', message: getApiError(e) });
                }
              }}
            >
              Restart Patroni Replication
            </Button>
            <Button
              variant="light"
              color="violet"
              loading={fioBusy}
              onClick={async () => {
                setFioBusy(true);
                try {
                  const { data } = await api.post<{
                    mode?: string;
                    duration_sec?: number;
                    result?: { ok?: boolean; error?: string; body?: unknown };
                  }>('/admin/storage/fio-test');
                  notifications.show({
                    color: data.result?.ok !== false ? 'teal' : 'orange',
                    message: `FIO ${data.duration_sec || 10}s: ${data.mode} · ${data.result?.error || 'ok'}`,
                  });
                } catch (e) {
                  notifications.show({ color: 'red', message: getApiError(e) });
                } finally {
                  setFioBusy(false);
                }
              }}
            >
              Запустить FIO-тест
            </Button>
            <Button
              variant="light"
              onClick={async () => {
                setLogsOpen(true);
                try {
                  const { data } = await api.get<{ containers: string[] }>(
                    '/admin/storage/docker-logs/containers',
                  );
                  setLogContainers(data.containers || []);
                  if (!logContainer && data.containers?.[0]) setLogContainer(data.containers[0]);
                } catch {
                  setLogContainers(['postgres', 'minio', 'patroni', 'redis']);
                }
              }}
            >
              Посмотреть логи
            </Button>
          </Group>
        }
      />
      <Modal
        opened={logsOpen}
        onClose={() => setLogsOpen(false)}
        title="Docker / Loki logs §11.16.4"
        size="xl"
      >
        <Stack>
          <Group>
            <Select
              label="Контейнер"
              data={(logContainers.length ? logContainers : ['postgres', 'minio', 'patroni', 'redis']).map(
                (c) => ({ value: c, label: c }),
              )}
              value={logContainer}
              onChange={setLogContainer}
              w={220}
              allowDeselect={false}
            />
            <Button
              mt={22}
              loading={logsLoading}
              onClick={async () => {
                if (!logContainer) return;
                setLogsLoading(true);
                try {
                  const { data } = await api.get<{
                    items?: Array<{ timestamp?: string; message?: string; level?: string }>;
                    backend?: string;
                    error?: string;
                    ok?: boolean;
                  }>('/admin/storage/docker-logs', {
                    params: { container: logContainer, limit: 200, minutes: 60 },
                  });
                  setLogLines(data.items || []);
                  setLogBackend(data.backend || '');
                  if (data.error) {
                    notifications.show({ color: 'orange', message: data.error });
                  }
                } catch (e) {
                  notifications.show({ color: 'red', message: getApiError(e) });
                } finally {
                  setLogsLoading(false);
                }
              }}
            >
              Загрузить
            </Button>
            {logBackend ? (
              <Text size="xs" c="dimmed" mt={28}>
                backend: {logBackend}
              </Text>
            ) : null}
          </Group>
          <ScrollArea h={420} offsetScrollbars>
            <Code block style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>
              {(logLines.length
                ? logLines.map((l) => `${l.timestamp || ''} [${l.level || 'INFO'}] ${l.message || ''}`).join('\n')
                : 'Выберите контейнер и нажмите «Загрузить»')}
            </Code>
          </ScrollArea>
        </Stack>
      </Modal>
      {lastCheck ? (
        <Text size="sm" c="dimmed" mb="sm">
          Last alert check: {lastCheck}
        </Text>
      ) : null}
      <SimpleGrid cols={{ base: 1, sm: 2 }} mb="lg">
        <HealthCard name="MinIO" status={health.ok ? 'Онлайн' : 'Ошибка'} load={health.ok ? 50 : 0} />
        <Card withBorder>
          <Text fw={600}>Шифрование SSE §10.6.3</Text>
          <Text size="sm" mt="sm">
            Режим: <b>{enc.mode || health.encryption?.mode || '—'}</b>
          </Text>
          <Text size="xs" c="dimmed" mt={4}>
            KMS key:{' '}
            {enc.kms_key_configured || health.encryption?.kms_key_configured
              ? enc.kms_key_id_masked || health.encryption?.kms_key_id_masked || 'yes'
              : 'не задан (fallback SSE-S3 при режиме sse-kms)'}
          </Text>
        </Card>
        <Card withBorder>
          <Text fw={600}>SMART / диск §11.16.5</Text>
          <Text size="sm" mt="sm">
            status: {health.smart?.status ?? '—'} · used:{' '}
            {health.used_percent != null ? `${health.used_percent}%` : '—'} · free:{' '}
            {health.free_percent != null ? `${health.free_percent}%` : '—'}
            {health.alert_disk_critical ? ' 🚨 critical' : health.alert_disk_high ? ' ⚠ >85%' : ''}
          </Text>
          <Text size="xs" c="dimmed" mt={4}>
            {health.smart?.note}
          </Text>
          {(health.smart_disks || []).length > 0 && (
            <ShellTable
              headers={['Device', 'Health', 'Temp', 'Realloc', 'Wear %']}
              rows={(health.smart_disks || []).map((d) => [
                d.device || d.model || '—',
                d.health || '—',
                d.temp_c != null ? `${d.temp_c}°C` : '—',
                d.reallocated_sectors != null ? String(d.reallocated_sectors) : '—',
                d.wear_percent != null || d.remaining_life_percent != null
                  ? String(d.wear_percent ?? d.remaining_life_percent)
                  : '—',
              ])}
            />
          )}
        </Card>
        <Card withBorder>
          <Text fw={600}>Репликация §11.16.2</Text>
          <Text size="sm" mt="sm">
            MinIO:{' '}
            {health.alert_replication_failed ? '⚠ Failed' : repl.length ? 'OK' : 'нет данных (MINIO_HA_JSON)'}
          </Text>
          {repl.length > 0 && (
            <ShellTable
              headers={['Bucket', 'Status', 'Pending', 'Failed min']}
              rows={repl.map((r) => [
                r.bucket || '—',
                r.status || '—',
                String(r.pending ?? r.pending_objects ?? '—'),
                r.failed_minutes != null ? String(r.failed_minutes) : r.failed_since || '—',
              ])}
            />
          )}
          <Text size="sm" mt="md">
            PostgreSQL: role={pg.role || '—'} · lag=
            {pg.lag_bytes != null ? `${Math.round(Number(pg.lag_bytes) / (1024 * 1024))} MB` : '—'} · wal=
            {pg.wal_state || pg.state || '—'}
          </Text>
          {nodes.length > 0 && (
            <ShellTable
              headers={['Node', 'Age sec', 'Last seen']}
              rows={nodes.map((n) => [
                n.id || n.name || '—',
                n.last_seen_age_sec != null ? String(n.last_seen_age_sec) : '—',
                n.last_seen || '—',
              ])}
            />
          )}
        </Card>
        <Card withBorder>
          <Text fw={600}>Write Activity Heartbeat §11.16 / §23.4</Text>
          <Text size="sm" mt="sm">
            load: {writeAct?.under_load ? 'да' : 'нет'} · queued={writeAct?.queued_tasks ?? '—'} ·
            processing={writeAct?.processing_tasks ?? '—'}
          </Text>
          <Text size="sm" mt={4}>
            last write: {writeAct?.last_write_at ?? '—'} · stale:{' '}
            {writeAct?.stale_seconds != null ? `${Math.round(writeAct.stale_seconds)}s` : '—'}
            {writeAct?.freeze_indicator ? ' 🔴 freeze' : ''}
          </Text>
          <Text size="xs" c="dimmed" mt={4}>
            PG tx/1h: {writeAct?.pg_tx_1h ?? '—'} · порог алерта 10 мин при нагрузке
          </Text>
          <Button
            mt="sm"
            size="xs"
            variant="light"
            onClick={async () => {
              try {
                const { data } = await api.post<{
                  freeze_indicator?: boolean;
                  critical?: boolean;
                  alert_sent?: boolean;
                  stale_seconds?: number;
                }>('/admin/write-activity/check');
                setWriteAct((prev) => ({ ...(prev || {}), ...data }));
                notifications.show({
                  color: data.critical ? 'red' : data.freeze_indicator ? 'orange' : 'teal',
                  message: `Write check: stale=${data.stale_seconds ?? '—'}s · critical=${String(data.critical)} · sent=${String(data.alert_sent)}`,
                });
              } catch (e) {
                notifications.show({ color: 'red', message: getApiError(e) });
              }
            }}
          >
            Check write→alerts
          </Button>
        </Card>
        <Card withBorder>
          <Text fw={600}>Node availability timeline §11.16.3</Text>
          <Group mt="xs" mb="sm" gap="sm">
            <Select
              label="Период"
              data={[
                { value: '7', label: '7 дней' },
                { value: '14', label: '14 дней' },
                { value: '30', label: '30 дней' },
              ]}
              value={timelineDays}
              onChange={(v) => {
                setTimelineDays(v || '7');
                void check();
              }}
              w={120}
            />
            <Select
              label="Узел"
              placeholder="Все узлы"
              clearable
              data={(timeline?.nodes || []).map((n) => ({
                value: n.node_id,
                label: n.node_name || n.node_id,
              }))}
              value={timelineNodeId}
              onChange={(v) => {
                setTimelineNodeId(v);
                void check();
              }}
              w={200}
            />
            <Button
              mt={22}
              variant="light"
              onClick={async () => {
                try {
                  const { data } = await api.get('/admin/storage/node-timeline/export', {
                    params: {
                      days: Number(timelineDays) || 7,
                      ...(timelineNodeId ? { node_id: timelineNodeId } : {}),
                    },
                    responseType: 'blob',
                  });
                  const url = URL.createObjectURL(data as Blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `node_timeline${timelineNodeId ? `_${timelineNodeId}` : ''}.csv`;
                  a.click();
                  URL.revokeObjectURL(url);
                } catch (e) {
                  notifications.show({ color: 'red', message: getApiError(e) });
                }
              }}
            >
              CSV
            </Button>
          </Group>
          <Text size="xs" c="dimmed" mb="sm">
            Heartbeat Tailscale · {timeline?.days || timelineDays}д
          </Text>
          {(timeline?.nodes || []).length === 0 && (
            <Text size="sm" c="dimmed">
              Нет событий — Celery sample или MINIO_HA_JSON nodes
            </Text>
          )}
          {(timeline?.nodes || []).map((n) => (
            <div key={n.node_id} style={{ marginBottom: 12 }}>
              <Group justify="space-between" mb={4}>
                <Text size="sm" fw={600}>
                  {n.node_name || n.node_id}
                </Text>
                <Text size="xs" c="dimmed">
                  uptime {n.uptime_percent ?? '—'}% · offline {n.offline_sec ?? 0}s
                </Text>
              </Group>
              <div
                style={{
                  display: 'flex',
                  height: 14,
                  borderRadius: 4,
                  overflow: 'hidden',
                  background: 'rgba(0,0,0,0.06)',
                }}
              >
                {(n.segments || []).slice(-40).map((s, i) => (
                  <div
                    key={`${n.node_id}-${i}`}
                    title={`${s.status} ${s.duration_sec}s`}
                    style={{
                      flex: Math.max(s.duration_sec, 1),
                      background: s.status === 'offline' ? '#c62828' : '#2e7d32',
                    }}
                  />
                ))}
              </div>
            </div>
          ))}
        </Card>
        <Card withBorder>
          <Text fw={600}>Disk fill forecast / wearout §23.7</Text>
          <Text size="sm" mt="sm">
            used: {forecast?.current_used_percent ?? '—'}% · рост:{' '}
            {forecast?.growth_percent_per_day != null ? `${forecast.growth_percent_per_day}%/день` : '—'}
          </Text>
          <Text size="sm" mt={4}>
            дней до 100%:{' '}
            <b style={{ color: forecast?.forecast_alert ? '#c62828' : undefined }}>
              {forecast?.days_until_full ?? '—'}
            </b>
            {forecast?.forecast_alert ? ' ⚠ ≤30д' : ''}
          </Text>
          {(forecast?.wearout || []).length > 0 && (
            <ShellTable
              headers={['Device', 'Wear %', 'Realloc', 'Replace?']}
              rows={(forecast?.wearout || []).map((w) => [
                w.device || '—',
                w.wear_percent != null ? String(w.wear_percent) : '—',
                w.reallocated_sectors != null ? String(w.reallocated_sectors) : '—',
                w.needs_replace || w.bad_sectors ? '⚠ да' : 'нет',
              ])}
            />
          )}
          {forecast?.wearout_alert ? (
            <Text size="xs" c="red" mt="xs">
              Wearout &lt;15% или битые сектора — планировать замену
            </Text>
          ) : null}
        </Card>
        <Card withBorder>
          <Text fw={600}>Buckets</Text>
          <Text size="sm" mt="sm">
            {(health.buckets || []).join(', ') || health.error || '—'}
          </Text>
        </Card>
        <Card withBorder>
          <Text fw={600}>Usage</Text>
          {(health.usage || []).map((u) => (
            <Text size="sm" key={u.bucket} mt={4}>
              {u.bucket}: {u.objects ?? 0} obj · {Math.round((u.bytes || 0) / 1024 / 1024)} MB
              {u.error ? ` (${u.error})` : ''}
            </Text>
          ))}
        </Card>
      </SimpleGrid>
    </>
  );
}
