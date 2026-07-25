import {
  Badge,
  Button,
  Checkbox,
  Group,
  Progress,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconChecklist, IconDownload, IconExternalLink, IconRefresh } from '@tabler/icons-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { api, getApiError } from '../services/api';

type CheckItem = { id: string; section: string; label: string };

type SoftKpi = {
  period_days: number;
  funnel: {
    generated: number;
    downloaded: number;
    links_added: number;
    verified: number;
    conversion?: Record<string, number>;
  };
  orders: {
    total: number;
    completed: number;
    cancelled: number;
    nsfw_blocked: number;
    cancel_rate: number;
    by_status: Record<string, number>;
  };
  finance: { revenue_rub: number; refunds_rub: number };
  models_created: number;
  kpi: {
    funnel_conversion: number;
    gen_to_download: number;
    target_conversion_60: boolean;
    cancel_rate_ok: boolean;
  };
  orders_daily: { day: string | null; count: number }[];
};

const FALLBACK_ITEMS: CheckItem[] = [
  { id: 'env', section: 'Секреты', label: 'Прод-секреты / шифрование ПД / хранилище секретов' },
  { id: 'yookassa', section: 'Секреты', label: 'ЮKassa + вебхук' },
  { id: 'vpn2fa', section: 'Секреты', label: 'VPN админа + двухфакторная аутентификация' },
  { id: 'alembic', section: 'Инфра', label: 'Миграции БД до последней версии' },
  { id: 'minio', section: 'Инфра', label: 'Бакеты MinIO + политики хранения' },
  { id: 'backup', section: 'Инфра', label: 'Резервная копия PG → MinIO' },
  { id: 'gpu_e2e', section: 'GPU', label: 'Сквозной тест TRELLIS.2 без заглушки' },
  { id: 'burn', section: 'GPU', label: 'Расход облака ₽/ч в лимите' },
  { id: 'tax', section: 'Платежи', label: 'Налоговый режим владельца' },
  { id: 'payment', section: 'Платежи', label: 'Тестовый платёж + чек' },
  { id: 'funnel', section: 'Продукт', label: 'Заказ → генерация → скачивание → верификация' },
  { id: 'b2b', section: 'Продукт', label: 'Корп. приглашения / роли / вебхуки' },
  { id: 'support', section: 'Поддержка', label: 'ЧаВО + создание/ответ тикета' },
  { id: 'nsfw', section: 'Поддержка', label: 'Очередь НСФВ + возврат' },
  { id: 'mobile', section: 'Мобильное', label: 'Наведённая съёмка «Купол» + термоконтроль + push-уведомления' },
  { id: 'alerts', section: 'Порог запуска', label: 'Алерты Telegram + план отката' },
];

function pct(v: number) {
  return `${Math.round(v * 1000) / 10}%`;
}

function BarRow({ label, value, max, color }: { label: string; value: number; max: number; color?: string }) {
  const p = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div>
      <Group justify="space-between" mb={4}>
        <Text size="sm">{label}</Text>
        <Text size="sm" c="#6d6c77">
          {value}
        </Text>
      </Group>
      <Progress value={p} color={color || 'brand'} size="sm" radius="sm" />
    </div>
  );
}

export default function SoftLaunchPage() {
  const [items, setItems] = useState<CheckItem[]>(FALLBACK_ITEMS);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [burn, setBurn] = useState<number | null>(null);
  const [kpi, setKpi] = useState<SoftKpi | null>(null);
  const [days, setDays] = useState<string | null>('7');
  const [loadingKpi, setLoadingKpi] = useState(false);
  const [savingCheck, setSavingCheck] = useState(false);

  const loadChecklist = useCallback(async () => {
    try {
      const { data } = await api.get<{
        items: CheckItem[];
        checks: Record<string, boolean>;
      }>('/admin/soft-launch/checklist');
      if (data.items?.length) setItems(data.items);
      setChecked(data.checks || {});
    } catch (e) {
      notifications.show({ color: 'yellow', message: getApiError(e) });
    }
  }, []);

  const loadBurn = useCallback(async () => {
    try {
      const { data } = await api.get<{ burn_rub_per_hour?: number }>('/admin/cloud/costs');
      setBurn(data.burn_rub_per_hour ?? 0);
    } catch (e) {
      notifications.show({ color: 'yellow', message: getApiError(e) });
    }
  }, []);

  const loadKpi = useCallback(async () => {
    setLoadingKpi(true);
    try {
      const { data } = await api.get<SoftKpi>('/admin/soft-launch/kpi', {
        params: { days: Number(days || 7) },
      });
      setKpi(data);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setLoadingKpi(false);
    }
  }, [days]);

  useEffect(() => {
    void loadBurn();
    void loadChecklist();
  }, [loadBurn, loadChecklist]);

  useEffect(() => {
    void loadKpi();
  }, [loadKpi]);

  async function toggle(id: string) {
    const next = { ...checked, [id]: !checked[id] };
    setChecked(next);
    setSavingCheck(true);
    try {
      const { data } = await api.put<{ checks: Record<string, boolean> }>(
        '/admin/soft-launch/checklist',
        { checks: next },
      );
      setChecked(data.checks || next);
    } catch (e) {
      setChecked(checked);
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setSavingCheck(false);
    }
  }

  const done = useMemo(() => Object.values(checked).filter(Boolean).length, [checked]);
  const sections = useMemo(() => [...new Set(items.map((i) => i.section))], [items]);
  const funnelMax = Math.max(
    kpi?.funnel.generated || 0,
    kpi?.funnel.downloaded || 0,
    kpi?.funnel.verified || 0,
    1,
  );
  const dailyMax = Math.max(...(kpi?.orders_daily.map((d) => d.count) || [1]), 1);

  return (
    <div className="vz-page">
      <div className="vz-page-header">
        <div>
          <Title order={2}>Мягкий запуск</Title>
          <Text c="#6d6c77" size="sm" mt={6}>
            КПЭ + чеклист (сервер) · {done}/{items.length}
            {savingCheck ? ' · сохранение…' : ''}
          </Text>
        </div>
        <Group>
          <Badge variant="light" color={burn != null && burn > 0 ? 'orange' : 'brand'}>
            Расход: {burn == null ? '—' : `${burn} ₽/ч`}
          </Badge>
          <Select
            data={[
              { value: '7', label: '7 дней' },
              { value: '14', label: '14 дней' },
              { value: '30', label: '30 дней' },
            ]}
            value={days}
            onChange={setDays}
            w={120}
            allowDeselect={false}
          />
          <Button
            leftSection={<IconRefresh size={16} />}
            variant="light"
            loading={loadingKpi}
            onClick={() => void loadKpi()}
          >
            КПЭ
          </Button>
          <Button
            leftSection={<IconDownload size={16} />}
            variant="light"
            onClick={async () => {
              try {
                const { data } = await api.get<Blob>('/admin/soft-launch/kpi/export', {
                  responseType: 'blob',
                  params: { days: Number(days || 7) },
                });
                const url = URL.createObjectURL(data);
                const a = document.createElement('a');
                a.href = url;
                a.download = `soft-launch-kpi-${days || 7}d.csv`;
                a.click();
                URL.revokeObjectURL(url);
              } catch (e) {
                notifications.show({ color: 'red', message: getApiError(e) });
              }
            }}
          >
            КПЭ CSV
          </Button>
          <Button leftSection={<IconChecklist size={16} />} variant="light" onClick={() => void loadChecklist()}>
            Чеклист
          </Button>
          <Button leftSection={<IconChecklist size={16} />} variant="light" onClick={() => void loadBurn()}>
            Расход
          </Button>
          <Button
            component="a"
            href="/docs/deployment/SOFT_LAUNCH.md"
            target="_blank"
            variant="default"
            leftSection={<IconExternalLink size={16} />}
            onClick={(e) => {
              e.preventDefault();
              notifications.show({
                color: 'blue',
                message: 'Полный чеклист: docs/deployment/SOFT_LAUNCH.md в репозитории',
              });
            }}
          >
            Документация
          </Button>
        </Group>
      </div>

      {kpi && (
        <SimpleGrid cols={{ base: 1, md: 2 }} mb="lg">
          <div className="vz-surface">
            <Group justify="space-between" mb="md">
              <Text fw={600}>Воронка публикации</Text>
              <Badge color={kpi.kpi.target_conversion_60 ? 'teal' : 'orange'} variant="light">
                конв. {pct(kpi.kpi.funnel_conversion)} {kpi.kpi.target_conversion_60 ? '≥60%' : '<60%'}
              </Badge>
            </Group>
            <Stack gap="sm">
              <BarRow label="Генерации" value={kpi.funnel.generated} max={funnelMax} />
              <BarRow label="Скачивания" value={kpi.funnel.downloaded} max={funnelMax} color="cyan" />
              <BarRow label="Ссылки" value={kpi.funnel.links_added} max={funnelMax} color="grape" />
              <BarRow label="Верификации" value={kpi.funnel.verified} max={funnelMax} color="teal" />
            </Stack>
            <Text size="xs" c="#6d6c77" mt="md">
              ген.→скач. {pct(kpi.kpi.gen_to_download)} · модели {kpi.models_created}
            </Text>
          </div>

          <div className="vz-surface">
            <Group justify="space-between" mb="md">
              <Text fw={600}>Заказы / финансы</Text>
              <Badge color={kpi.kpi.cancel_rate_ok ? 'teal' : 'red'} variant="light">
                отмены {pct(kpi.orders.cancel_rate)}
              </Badge>
            </Group>
            <SimpleGrid cols={2} mb="md">
              <div>
                <Text size="xs" c="#6d6c77">
                  Всего
                </Text>
                <Text fw={700}>{kpi.orders.total}</Text>
              </div>
              <div>
                <Text size="xs" c="#6d6c77">
                  Завершено
                </Text>
                <Text fw={700}>{kpi.orders.completed}</Text>
              </div>
              <div>
                <Text size="xs" c="#6d6c77">
                  Выручка
                </Text>
                <Text fw={700}>{kpi.finance.revenue_rub} ₽</Text>
              </div>
              <div>
                <Text size="xs" c="#6d6c77">
                  Блокировки НСФВ
                </Text>
                <Text fw={700}>{kpi.orders.nsfw_blocked}</Text>
              </div>
            </SimpleGrid>
            <Text size="sm" fw={600} mb="xs">
              Заказы по дням
            </Text>
            <Stack gap={6}>
              {(kpi.orders_daily.length ? kpi.orders_daily : [{ day: '—', count: 0 }]).map((d) => (
                <BarRow key={String(d.day)} label={d.day || '—'} value={d.count} max={dailyMax} color="orange" />
              ))}
            </Stack>
          </div>
        </SimpleGrid>
      )}

      <div className="vz-grid vz-grid-2-lg">
        {sections.map((section) => (
          <div key={section} className="vz-surface">
            <Text fw={600} mb="md">
              {section}
            </Text>
            <Stack gap="sm">
              {items
                .filter((i) => i.section === section)
                .map((item) => (
                  <Checkbox
                    key={item.id}
                    label={item.label}
                    checked={!!checked[item.id]}
                    onChange={() => void toggle(item.id)}
                  />
                ))}
            </Stack>
          </div>
        ))}
      </div>
    </div>
  );
}
