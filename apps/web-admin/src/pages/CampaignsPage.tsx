import {
  Button,
  Center,
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
  stats?: { reach?: number; sent?: number; roi?: number; revenue_rub?: number };
  budget_rub?: number | null;
  created_at?: string;
};

const SEGMENTS = [
  { value: '{}', label: 'Все с marketing_opt_in' },
  { value: '{"account_type":"individual"}', label: 'Физлица' },
  { value: '{"account_type":"legal"}', label: 'Юрлица' },
  { value: '{"has_orders":true}', label: 'С заказами' },
  { value: '{"min_balance":1000}', label: 'Баланс ≥ 1000' },
];

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
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);

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
        config: { title: title || name, body, channel: 'email' },
        budget_rub: Number(budget) || 0,
      });
      setOpened(false);
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
      const { data } = await api.get(`/admin/campaigns/${id}/stats`);
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

  return (
    <>
      <PageHeader
        title="Кампании"
        description="Конструктор, сегменты, ROI"
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
        {stats && (
          <Text size="sm" c="dimmed">
            Stats: reach={String(stats.reach)} sent={String(stats.sent)} revenue={String(stats.revenue_rub)} ROI=
            {String(stats.roi)}
          </Text>
        )}
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
            <Button size="xs" variant="subtle" onClick={() => showStats(c.id)}>
              ROI
            </Button>
          </Group>,
        ])}
      />
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
          <NumberInput label="Бюджет, ₽" value={budget} onChange={setBudget} min={0} />
          <Button onClick={createDraft}>Сохранить черновик</Button>
        </Stack>
      </Modal>
    </>
  );
}
