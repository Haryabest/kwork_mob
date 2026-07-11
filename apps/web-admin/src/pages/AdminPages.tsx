import { ActionIcon, Button, Card, Center, Group, Loader, Modal, NumberInput, Select, SimpleGrid, Slider, Stack, Tabs, Text, TextInput, Textarea } from '@mantine/core';
import { IconPlus, IconRefresh, IconTrash } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';
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
  }>>([]);
  const [summary, setSummary] = useState({ online: 0, total: 0, queue_normal: 0, queue_high: 0 });
  const [loading, setLoading] = useState(true);

  async function load() {
    const { data } = await api.get<{ summary: typeof summary; items: typeof items }>('/admin/workers');
    setSummary(data.summary);
    setItems(data.items ?? []);
  }

  useEffect(() => {
    load().catch((e) => notifications.show({ color: 'red', message: getApiError(e) })).finally(() => setLoading(false));
  }, []);

  if (loading) return <Center py="xl"><Loader color="brand" /></Center>;

  return (
    <>
      <PageHeader
        title="Воркеры"
        description="Состояние GPU-очередей и распределение нагрузки"
        action={
          <Button leftSection={<IconRefresh size={16} />} onClick={() => load()}>
            Обновить
          </Button>
        }
      />
      <MetricGrid
        items={[
          { label: 'Онлайн', value: String(summary.online), hint: `из ${summary.total}`, color: 'teal' },
          { label: 'Очередь normal', value: String(summary.queue_normal) },
          { label: 'Очередь high', value: String(summary.queue_high) },
          { label: 'Всего воркеров', value: String(summary.total) },
        ]}
      />
      <ShellTable
        headers={['Воркер', 'Статус', 'GPU', 'Вес', 'Grace', 'Действия']}
        rows={
          items.length
            ? items.map((w) => [
                w.id,
                <StateBadge key={`s-${w.id}`} value={w.status} color={w.status === 'online' ? 'teal' : 'orange'} />,
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
                <Button
                  key={`g-${w.id}`}
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
                  Grace 30 сек
                </Button>,
              ])
            : [['—', 'Нет воркеров', 'Heartbeat ещё не приходил', '—', '—', '—']]
        }
      />
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

export function CompanyDetailPage() {
  const { id } = useParams();
  const [company, setCompany] = useState<{
    id: number;
    name: string;
    inn: string;
    balance: number;
    status: string;
    members: Array<{ user_id: number; role: string }>;
  } | null>(null);
  const [stats, setStats] = useState({ orders: 0, revenue: 0 });

  async function load() {
    const [c, s] = await Promise.all([api.get(`/admin/companies/${id}`), api.get(`/admin/companies/${id}/stats`)]);
    setCompany(c.data);
    setStats(s.data);
  }

  useEffect(() => {
    load().catch((e) => notifications.show({ color: 'red', message: getApiError(e) }));
  }, [id]);

  if (!company) return <Center py="xl"><Loader color="brand" /></Center>;

  return (
    <>
      <PageHeader title={company.name} description={`ИНН ${company.inn} · статус ${company.status}`} />
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <Card withBorder>
          <Stack>
            <Text fw={600}>Реквизиты</Text>
            <Text size="sm">Баланс: {company.balance.toLocaleString('ru-RU')} ₽</Text>
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
          <Text fw={600} mb="sm">Сотрудники</Text>
          <ShellTable headers={['User ID', 'Роль']} rows={company.members.map((m) => [String(m.user_id), m.role])} />
        </Card>
      </SimpleGrid>
    </>
  );
}

export function InvitationsPage() {
  return (
    <>
      <PageHeader title="Приглашения" description="Активные приглашения сотрудников в B2B-компании" />
      <ShellTable
        headers={['Email', 'Компания', 'Роль', 'Срок', '']}
        rows={[
          [
            'designer@mercury.ru',
            'ООО «Меркурий»',
            'Дизайнер',
            '13.07.2026',
            <ActionIcon key="1" color="red" variant="light">
              <IconTrash size={16} />
            </ActionIcon>,
          ],
        ]}
      />
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

export function LogsPage() {
  return (
    <>
      <PageHeader title="Логи" description="События сервисов" />
      <ShellTable
        headers={['Время', 'Уровень', 'Источник', 'Сообщение']}
        rows={[['—', <StateBadge key="i" value="INFO" color="blue" />, 'api', 'Подключите централизованный сбор логов']]}
      />
    </>
  );
}

export function StoragePage() {
  const [health, setHealth] = useState<{ ok?: boolean; buckets?: string[]; error?: string }>({});

  async function check() {
    try {
      const { data } = await api.get('/storage/health');
      setHealth(data);
    } catch (e) {
      setHealth({ ok: false, error: getApiError(e) });
    }
  }

  useEffect(() => {
    check();
  }, []);

  return (
    <>
      <PageHeader
        title="Кластер хранения"
        description="Здоровье MinIO"
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
          </Group>
        }
      />
      <SimpleGrid cols={{ base: 1, sm: 2 }} mb="lg">
        <HealthCard name="MinIO" status={health.ok ? 'Онлайн' : 'Ошибка'} load={health.ok ? 50 : 0} />
        <Card withBorder>
          <Text fw={600}>Buckets</Text>
          <Text size="sm" mt="sm">
            {(health.buckets || []).join(', ') || health.error || '—'}
          </Text>
        </Card>
      </SimpleGrid>
    </>
  );
}
