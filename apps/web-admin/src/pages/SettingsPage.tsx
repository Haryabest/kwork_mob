import { Button, Card, Center, Group, Loader, NumberInput, SimpleGrid, Stack, Switch, TextInput, Text } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';
import { PageHeader, ShellTable, StateBadge } from '../components/Panel';
import { api, getApiError } from '../services/api';

type Tariff = { code: string; title: string; amount_rub: number };
type Hist = { id: number; tariff_code: string; old_amount: number; new_amount: number; created_at?: string };
type Esc = {
  task_id: string;
  order_id: number;
  status: string;
  escalation_count: number;
  priority: string;
  updated_at?: string;
};

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [tariffs, setTariffs] = useState<Tariff[]>([]);
  const [small, setSmall] = useState<number | string>(2990);
  const [large, setLarge] = useState<number | string>(5990);
  const [history, setHistory] = useState<Hist[]>([]);
  const [esc, setEsc] = useState<Esc[]>([]);
  const [tgEnabled, setTgEnabled] = useState(false);
  const [tgToken, setTgToken] = useState('');
  const [tgChat, setTgChat] = useState('');

  async function load() {
    const [t, h, a, e] = await Promise.all([
      api.get<{ items: Tariff[] }>('/admin/tariffs'),
      api.get<{ items: Hist[] }>('/admin/tariffs/history'),
      api.get<{ telegram_enabled: boolean; telegram_chat_id?: string; telegram_bot_token_set: boolean }>(
        '/admin/alerts/settings',
      ),
      api.get<{ items: Esc[] }>('/admin/escalations'),
    ]);
    setTariffs(t.data.items ?? []);
    const sm = t.data.items?.find((x) => x.code === 'small');
    const lg = t.data.items?.find((x) => x.code === 'large');
    if (sm) setSmall(sm.amount_rub);
    if (lg) setLarge(lg.amount_rub);
    setHistory(h.data.items ?? []);
    setTgEnabled(a.data.telegram_enabled);
    setTgChat(a.data.telegram_chat_id ?? '');
    setEsc(e.data.items ?? []);
  }

  useEffect(() => {
    load()
      .catch((err) => notifications.show({ color: 'red', message: getApiError(err) }))
      .finally(() => setLoading(false));
  }, []);

  async function saveTariffs() {
    try {
      await api.patch('/admin/tariffs/small', { amount_rub: Number(small), note: 'admin UI' });
      await api.patch('/admin/tariffs/large', { amount_rub: Number(large), note: 'admin UI' });
      notifications.show({ color: 'teal', message: 'Тарифы сохранены' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  async function saveAlerts() {
    try {
      await api.put('/admin/alerts/settings', {
        telegram_enabled: tgEnabled,
        telegram_bot_token: tgToken || undefined,
        telegram_chat_id: tgChat || undefined,
      });
      notifications.show({ color: 'teal', message: 'Алерты сохранены' });
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  async function testAlert() {
    try {
      const { data } = await api.post<{ ok: boolean }>('/admin/alerts/test', {
        message: 'Тест алерта KWork / эскалации',
      });
      notifications.show({
        color: data.ok ? 'teal' : 'orange',
        message: data.ok ? 'Отправлено в Telegram' : 'Не отправлено (проверьте token/chat)',
      });
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

  return (
    <>
      <PageHeader title="Настройки" description="Тарифы, Telegram-алерты, эскалации" />
      <Stack gap="lg">
        <Card withBorder>
          <Text fw={600} mb="sm">
            Тарифы
          </Text>
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <NumberInput label="Малый, ₽" value={small} onChange={setSmall} min={1} />
            <NumberInput label="Крупный, ₽" value={large} onChange={setLarge} min={1} />
          </SimpleGrid>
          <Button mt="md" onClick={() => void saveTariffs()}>
            Сохранить тарифы
          </Button>
          <Text size="sm" c="dimmed" mt="md">
            Текущие: {tariffs.map((t) => `${t.code}=${t.amount_rub}`).join(', ')}
          </Text>
        </Card>

        <Card withBorder>
          <Text fw={600} mb="sm">
            История цен
          </Text>
          <ShellTable
            headers={['Тариф', 'Было', 'Стало', 'Когда']}
            rows={
              history.length
                ? history.slice(0, 20).map((h) => [
                    h.tariff_code,
                    String(h.old_amount),
                    String(h.new_amount),
                    h.created_at ?? '—',
                  ])
                : [['—', 'Нет изменений', '—', '—']]
            }
          />
        </Card>

        <Card withBorder>
          <Text fw={600} mb="sm">
            Telegram-алерты (эскалации / NSFW)
          </Text>
          <Stack>
            <Switch label="Включить Telegram" checked={tgEnabled} onChange={(e) => setTgEnabled(e.currentTarget.checked)} />
            <TextInput
              label="Bot token"
              type="password"
              placeholder="оставьте пустым, чтобы не менять"
              value={tgToken}
              onChange={(e) => setTgToken(e.currentTarget.value)}
            />
            <TextInput label="Chat ID" value={tgChat} onChange={(e) => setTgChat(e.currentTarget.value)} />
            <Group>
              <Button onClick={() => void saveAlerts()}>Сохранить алерты</Button>
              <Button variant="light" onClick={() => void testAlert()}>
                Тест
              </Button>
            </Group>
          </Stack>
        </Card>

        <Card withBorder>
          <Text fw={600} mb="sm">
            Эскалации очереди
          </Text>
          <ShellTable
            headers={['Task', 'Заказ', 'Статус', 'Count', 'Priority', 'Обновлён']}
            rows={
              esc.length
                ? esc.map((x) => [
                    x.task_id.slice(0, 8),
                    String(x.order_id),
                    <StateBadge key={x.task_id} value={x.status} />,
                    String(x.escalation_count),
                    x.priority,
                    x.updated_at ?? '—',
                  ])
                : [['—', 'Нет эскалаций', '—', '—', '—', '—']]
            }
          />
        </Card>
      </Stack>
    </>
  );
}
