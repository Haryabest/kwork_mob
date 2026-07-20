import {
  Button,
  Card,
  Center,
  Group,
  Loader,
  NumberInput,
  SimpleGrid,
  Stack,
  Switch,
  TagsInput,
  TextInput,
  Text,
} from '@mantine/core';
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

type Thresholds = Record<string, number>;

const THRESHOLD_LABELS: Record<string, string> = {
  queue_alert_length: 'Длина очереди',
  all_busy_alert_minutes: 'Все busy, мин',
  worker_offline_alert_seconds: 'Worker offline, сек',
  gpu_temp_alert_c: 'GPU temp, °C',
  yookassa_error_streak: 'YooKassa errors streak',
  yookassa_webhook_fail_streak: 'YooKassa webhook fail streak',
  company_webhook_fail_streak: 'Company webhook fail streak',
  company_low_balance_rub: 'Низкий баланс компании, ₽',
  company_suspicious_orders_10m: 'Подозрительные заказы / окно',
  company_suspicious_window_min: 'Окно подозрительности, мин',
  shoot_link_mass_limit_per_hour: 'Shoot-link mass / час',
  shoot_link_mass_block_hours: 'Shoot-link block, ч',
  publication_conversion_alert_ratio: 'Конверсия публикации (доля)',
  fallback_segmentation_alert_ratio: 'Fallback сегментация (доля)',
  api_key_default_daily_limit: 'API key daily default',
  storage_disk_free_min_percent: 'Disk free min %',
  storage_ssd_wear_min_percent: 'SSD remaining min %',
  storage_temp_alert_c: 'Storage temp °C',
  storage_pg_lag_alert_bytes: 'PG lag bytes',
  storage_minio_repl_fail_minutes: 'MinIO repl fail, мин',
  storage_node_offline_seconds: 'Storage node offline, сек',
  storage_write_stale_minutes: 'Write stale (нагрузка), мин',
  storage_write_freeze_minutes: 'Write freeze indicator, мин',
  cloud_monthly_budget_rub: 'Cloud GPU budget месяц, ₽ (0=∞)',
  cloud_daily_budget_rub: 'Cloud GPU budget день, ₽ (0=∞)',
  cloud_burn_alert_rub_per_hour: 'Cloud burn alert, ₽/ч',
  analytics_ch_sync_pending_max: 'Analytics CH sync backlog max',
};

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [tariffs, setTariffs] = useState<Tariff[]>([]);
  const [small, setSmall] = useState<number | string>(2990);
  const [large, setLarge] = useState<number | string>(5990);
  const [importGlb, setImportGlb] = useState<number | string>(500);
  const [history, setHistory] = useState<Hist[]>([]);
  const [esc, setEsc] = useState<Esc[]>([]);
  const [tgEnabled, setTgEnabled] = useState(false);
  const [tgToken, setTgToken] = useState('');
  const [tgChat, setTgChat] = useState('');
  const [emailEnabled, setEmailEnabled] = useState(false);
  const [emailRecipients, setEmailRecipients] = useState<string[]>([]);
  const [thresholds, setThresholds] = useState<Thresholds>({});

  async function load() {
    const [t, h, a, e] = await Promise.all([
      api.get<{ items: Tariff[] }>('/admin/tariffs'),
      api.get<{ items: Hist[] }>('/admin/tariffs/history'),
      api.get<{
        telegram_enabled: boolean;
        telegram_chat_id?: string;
        telegram_bot_token_set: boolean;
        email_enabled?: boolean;
        email_to?: string;
        email_recipients?: string[];
        thresholds?: Thresholds;
      }>('/admin/alerts/settings'),
      api.get<{ items: Esc[] }>('/admin/escalations'),
    ]);
    setTariffs(t.data.items ?? []);
    const sm = t.data.items?.find((x) => x.code === 'small');
    const lg = t.data.items?.find((x) => x.code === 'large');
    const imp = t.data.items?.find((x) => x.code === 'import_glb');
    if (sm) setSmall(sm.amount_rub);
    if (lg) setLarge(lg.amount_rub);
    if (imp) setImportGlb(imp.amount_rub);
    setHistory(h.data.items ?? []);
    setTgEnabled(a.data.telegram_enabled);
    setTgChat(a.data.telegram_chat_id ?? '');
    setEmailEnabled(Boolean(a.data.email_enabled));
    const rec =
      a.data.email_recipients && a.data.email_recipients.length
        ? a.data.email_recipients
        : (a.data.email_to || '')
            .split(/[,;]/)
            .map((x) => x.trim())
            .filter(Boolean);
    setEmailRecipients(rec.slice(0, 5));
    setThresholds(a.data.thresholds ?? {});
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
      await api.patch('/admin/tariffs/import_glb', { amount_rub: Number(importGlb), note: 'admin UI' });
      notifications.show({ color: 'teal', message: 'Тарифы сохранены' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  async function saveAlerts() {
    try {
      const clean = emailRecipients.map((x) => x.trim()).filter(Boolean).slice(0, 5);
      await api.put('/admin/alerts/settings', {
        telegram_enabled: tgEnabled,
        telegram_bot_token: tgToken || undefined,
        telegram_chat_id: tgChat || undefined,
        email_enabled: emailEnabled,
        email_recipients: clean,
        email_to: clean.join(', '),
        thresholds,
      });
      notifications.show({ color: 'teal', message: 'Алерты и пороги сохранены' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  async function testAlert(channel: string) {
    try {
      const { data } = await api.post<{ ok: boolean; telegram?: boolean; email?: boolean }>(
        '/admin/alerts/test',
        { message: 'Тест алерта KWork / эскалации', channel },
      );
      notifications.show({
        color: data.ok ? 'teal' : 'orange',
        message: data.ok
          ? `Отправлено (tg=${String(data.telegram)} email=${String(data.email)})`
          : 'Не отправлено (проверьте token/chat/email)',
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

  const thresholdKeys = Object.keys(THRESHOLD_LABELS).filter((k) => k in thresholds);

  return (
    <>
      <PageHeader title="Настройки" description="Тарифы, алерты §12.4.1–12.4.2, пороги, эскалации" />
      <Stack gap="lg">
        <Card withBorder>
          <Text fw={600} mb="sm">
            Тарифы
          </Text>
          <SimpleGrid cols={{ base: 1, sm: 3 }}>
            <NumberInput label="Малый, ₽" value={small} onChange={setSmall} min={1} />
            <NumberInput label="Крупный, ₽" value={large} onChange={setLarge} min={1} />
            <NumberInput
              label="Импорт GLB, ₽"
              description="§6.10 · 0 = бесплатно"
              value={importGlb}
              onChange={setImportGlb}
              min={0}
            />
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
            Каналы алертов (Telegram / Email §12.4.2)
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
            <Switch label="Включить Email" checked={emailEnabled} onChange={(e) => setEmailEnabled(e.currentTarget.checked)} />
            <TagsInput
              label="Email получатели (до 5)"
              description="Enter / запятая — новый адрес"
              value={emailRecipients}
              onChange={(v) => setEmailRecipients(v.slice(0, 5))}
              maxTags={5}
              placeholder="ops@example.com"
              splitChars={[',', ';', ' ']}
            />
            <Group>
              <Button onClick={() => void saveAlerts()}>Сохранить алерты</Button>
              <Button variant="light" onClick={() => void testAlert('dual')}>
                Тест dual
              </Button>
              <Button variant="light" onClick={() => void testAlert('telegram')}>
                Тест TG
              </Button>
              <Button variant="light" onClick={() => void testAlert('email')}>
                Тест Email
              </Button>
            </Group>
          </Stack>
        </Card>

        <Card withBorder>
          <Text fw={600} mb="sm">
            Пороги алертов §12.4.1 / §11.16.5
          </Text>
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }}>
            {thresholdKeys.map((key) => {
              const isRatio = key.includes('ratio');
              return (
                <NumberInput
                  key={key}
                  label={THRESHOLD_LABELS[key] ?? key}
                  value={thresholds[key]}
                  decimalScale={isRatio ? 2 : 0}
                  step={isRatio ? 0.01 : 1}
                  min={0}
                  onChange={(v) =>
                    setThresholds((prev) => ({
                      ...prev,
                      [key]: typeof v === 'number' ? v : Number(v) || 0,
                    }))
                  }
                />
              );
            })}
          </SimpleGrid>
          <Button mt="md" onClick={() => void saveAlerts()}>
            Сохранить пороги
          </Button>
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
