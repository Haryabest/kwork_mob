import {
  Badge,
  Button,
  Center,
  Checkbox,
  Group,
  Loader,
  Modal,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Textarea,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';
import { MetricGrid, PageHeader, ShellTable, StateBadge } from '../components/Panel';
import { api, getApiError } from '../services/api';

type Campaign = {
  id: number;
  name: string;
  template?: string;
  status: string;
  stats?: { reach?: number; sent?: number; roi?: number; revenue_rub?: number; clicked?: number };
  budget_rub?: number | null;
  created_at?: string;
};

type CampaignStats = {
  id: number;
  name: string;
  ab_enabled?: boolean;
  reach?: number;
  sent?: number;
  failed?: number;
  clicked?: number;
  ctr?: number;
  revenue_rub?: number;
  cost_rub?: number;
  roi?: number | null;
  by_variant?: Record<string, { sent?: number; failed?: number; clicks?: number }>;
  funnel?: { reach?: number; sent?: number; clicked?: number; converted?: number };
};

const SEGMENTS = [
  { value: '{}', label: 'Все с marketing_opt_in' },
  { value: '{"account_type":"individual"}', label: 'Физлица' },
  { value: '{"account_type":"legal"}', label: 'Юрлица' },
  { value: '{"has_orders":true}', label: 'С заказами' },
  { value: '{"min_balance":1000}', label: 'Баланс ≥ 1000' },
];

/** §11.7 — кампании + A/B stats */
export default function CampaignsPage() {
  const [items, setItems] = useState<Campaign[]>([]);
  const [templates, setTemplates] = useState<{ code: string; title: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [opened, setOpened] = useState(false);
  const [name, setName] = useState('');
  const [template, setTemplate] = useState<string | null>('promo_discount');
  const [segment, setSegment] = useState<string | null>(SEGMENTS[0].value);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [budget, setBudget] = useState<number | string>(0);
  const [abEnabled, setAbEnabled] = useState(false);
  const [ctaUrl, setCtaUrl] = useState('');
  const [stats, setStats] = useState<CampaignStats | null>(null);

  async function load() {
    const [c, t] = await Promise.all([
      api.get<{ items: Campaign[] }>('/admin/campaigns'),
      api.get<{ items: { code: string; title: string }[] }>('/admin/campaigns/templates'),
    ]);
    setItems(c.data.items ?? []);
    setTemplates(t.data.items ?? []);
  }

  useEffect(() => {
    load()
      .catch((e) => notifications.show({ color: 'red', message: getApiError(e) }))
      .finally(() => setLoading(false));
  }, []);

  async function createDraft() {
    try {
      await api.post('/admin/campaigns', {
        name,
        template,
        segment: JSON.parse(segment || '{}'),
        config: {
          title: title || name,
          body,
          channel: 'email',
          ab_enabled: abEnabled,
          variants: ['A', 'B'],
          cta_url: ctaUrl.trim() || undefined,
          cta_label: 'Открыть',
        },
        budget_rub: Number(budget) || 0,
      });
      setOpened(false);
      setAbEnabled(false);
      setCtaUrl('');
      notifications.show({ color: 'teal', message: 'Черновик создан' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  async function start(id: number) {
    try {
      await api.post(`/admin/campaigns/${id}/start`);
      notifications.show({ color: 'teal', message: 'Кампания запущена' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  async function stop(id: number) {
    try {
      await api.post(`/admin/campaigns/${id}/stop`);
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  async function showStats(id: number) {
    try {
      const { data } = await api.get<CampaignStats>(`/admin/campaigns/${id}/stats`);
      setStats(data);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  if (loading) {
    return (
      <Center py="xl">
        <Loader color="brand" />
      </Center>
    );
  }

  const last = items[0]?.stats;
  const variantRows = stats?.by_variant
    ? Object.entries(stats.by_variant).map(([v, s]) => [
        v,
        String(s.sent ?? 0),
        String(s.clicks ?? 0),
        String(s.failed ?? 0),
        s.sent ? `${(((s.clicks ?? 0) / s.sent) * 100).toFixed(1)}%` : '—',
      ])
    : [];

  return (
    <>
      <PageHeader
        title="Кампании"
        description="Конструктор, A/B, воронка ROI (§11.7)"
        action={<Button onClick={() => setOpened(true)}>Новая кампания</Button>}
      />
      <SimpleGrid cols={{ base: 1, lg: 2 }} mb="md">
        <MetricGrid
          items={[
            { label: 'Охват (последняя)', value: String(last?.reach ?? '—') },
            { label: 'Отправлено', value: String(last?.sent ?? '—') },
            { label: 'ROI', value: last?.roi != null ? String(last.roi) : '—' },
          ]}
        />
      </SimpleGrid>
      <ShellTable
        headers={['ID', 'Название', 'Шаблон', 'Статус', 'Бюджет', 'Действия']}
        rows={items.map((c) => [
          String(c.id),
          c.name,
          c.template ?? '—',
          <StateBadge key={`s${c.id}`} value={c.status} />,
          c.budget_rub != null ? `${c.budget_rub} ₽` : '—',
          <Group key={`a${c.id}`} gap="xs">
            <Button size="xs" onClick={() => start(c.id)} disabled={c.status === 'running'}>
              Старт
            </Button>
            <Button size="xs" variant="light" onClick={() => stop(c.id)}>
              Стоп
            </Button>
            <Button size="xs" variant="subtle" onClick={() => void showStats(c.id)}>
              A/B · ROI
            </Button>
          </Group>,
        ])}
      />

      <Modal opened={!!stats} onClose={() => setStats(null)} title={stats ? `Статистика: ${stats.name}` : ''} size="lg">
        {stats && (
          <Stack gap="md">
            <Group gap="xs">
              {stats.ab_enabled && <Badge color="violet">A/B</Badge>}
              <Badge variant="light">CTR {(Number(stats.ctr || 0) * 100).toFixed(2)}%</Badge>
            </Group>
            <MetricGrid
              items={[
                { label: 'Reach', value: String(stats.funnel?.reach ?? stats.reach ?? 0) },
                { label: 'Sent', value: String(stats.funnel?.sent ?? stats.sent ?? 0) },
                { label: 'Clicked', value: String(stats.funnel?.clicked ?? stats.clicked ?? 0) },
                { label: 'Converted', value: String(stats.funnel?.converted ?? 0) },
                { label: 'Revenue', value: `${stats.revenue_rub ?? 0} ₽` },
                { label: 'ROI', value: stats.roi != null ? String(stats.roi) : '—' },
              ]}
            />
            {variantRows.length > 0 && (
              <>
                <Text fw={600} size="sm">
                  По вариантам A/B
                </Text>
                <ShellTable headers={['Variant', 'Sent', 'Clicks', 'Failed', 'CTR']} rows={variantRows} />
              </>
            )}
          </Stack>
        )}
      </Modal>

      <Modal opened={opened} onClose={() => setOpened(false)} title="Новая кампания" size="lg">
        <Stack>
          <TextInput label="Название" value={name} onChange={(e) => setName(e.currentTarget.value)} />
          <Select
            label="Шаблон"
            value={template}
            onChange={setTemplate}
            data={templates.map((t) => ({ value: t.code, label: t.title }))}
          />
          <Select label="Сегмент" value={segment} onChange={setSegment} data={SEGMENTS} />
          <TextInput label="Заголовок письма" value={title} onChange={(e) => setTitle(e.currentTarget.value)} />
          <Textarea label="Текст" minRows={4} value={body} onChange={(e) => setBody(e.currentTarget.value)} />
          <TextInput
            label="CTA URL (через click tracker)"
            description="Ссылка в письме пойдёт через GET /api/v1/campaigns/{id}/click"
            placeholder="https://…"
            value={ctaUrl}
            onChange={(e) => setCtaUrl(e.currentTarget.value)}
          />
          <NumberInput label="Бюджет, ₽" value={budget} onChange={setBudget} min={0} />
          <Checkbox
            label="A/B тест (варианты A/B при старте)"
            checked={abEnabled}
            onChange={(e) => setAbEnabled(e.currentTarget.checked)}
          />
          <Button onClick={() => void createDraft()}>Сохранить черновик</Button>
        </Stack>
      </Modal>
    </>
  );
}
