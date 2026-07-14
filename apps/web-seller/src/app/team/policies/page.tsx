'use client';

import {
  Button,
  Checkbox,
  Divider,
  MultiSelect,
  NumberInput,
  Select,
  Stack,
  Switch,
  Text,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';
import { SellerShell } from '../../../components/SellerShell';
import { api, apiMessage } from '../../../services/api';

type Policies = {
  default_max_concurrent_orders: number;
  default_monthly_spending_limit: number | null;
  default_allowed_categories: string[];
  allow_photographer_download: boolean;
  allow_photographer_add_links: boolean;
  require_2fa_for_all: boolean;
  auto_block_inactive_days: number;
  low_balance_threshold: number;
};

type Routing = Record<string, string>;

const EMPTY: Policies = {
  default_max_concurrent_orders: 5,
  default_monthly_spending_limit: null,
  default_allowed_categories: [],
  allow_photographer_download: true,
  allow_photographer_add_links: true,
  require_2fa_for_all: false,
  auto_block_inactive_days: 90,
  low_balance_threshold: 5000,
};

const ROUTING_DEFAULT: Routing = {
  generation_done: 'owner_manager',
  photographer_uploaded: 'owner_manager',
  source_expire: 'all',
  low_balance: 'owner_only',
};

const EVENT_LABELS: Record<string, string> = {
  generation_done: 'Генерация завершена',
  photographer_uploaded: 'Фотограф загрузил фото',
  source_expire: 'Истекает облачная копия',
  low_balance: 'Низкий баланс компании',
};

const AUDIENCE_OPTIONS = [
  { value: 'owner_only', label: 'Только Owner' },
  { value: 'owner_manager', label: 'Owner + Manager' },
  { value: 'all', label: 'Всем сотрудникам' },
];

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Policies>(EMPTY);
  const [routing, setRouting] = useState<Routing>(ROUTING_DEFAULT);
  const [categories, setCategories] = useState<string[]>([]);
  const [balance, setBalance] = useState<number | null>(null);
  const [noMonthlyLimit, setNoMonthlyLimit] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .get<{
        policies: Policies;
        notification_routing?: Routing;
        available_categories: string[];
        balance: number;
      }>('/company/settings')
      .then(({ data }) => {
        const p = { ...EMPTY, ...(data.policies || {}) };
        setPolicies(p);
        setRouting({ ...ROUTING_DEFAULT, ...(data.notification_routing || {}) });
        setNoMonthlyLimit(p.default_monthly_spending_limit == null);
        setCategories(data.available_categories || []);
        setBalance(data.balance);
      })
      .catch((e) => notifications.show({ color: 'red', message: apiMessage(e) }));
  }, []);

  async function save() {
    setSaving(true);
    try {
      const payload = {
        policies: {
          ...policies,
          default_monthly_spending_limit: noMonthlyLimit
            ? null
            : policies.default_monthly_spending_limit,
        },
        notification_routing: routing,
      };
      const { data } = await api.patch<{
        policies: Policies;
        notification_routing?: Routing;
      }>('/company/settings', payload);
      setPolicies({ ...EMPTY, ...(data.policies || {}) });
      setRouting({ ...ROUTING_DEFAULT, ...(data.notification_routing || {}) });
      notifications.show({ color: 'teal', message: 'Политики сохранены' });
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setSaving(false);
    }
  }

  return (
    <SellerShell>
      <Title order={2} mb="xs">
        Политики доступа (§2.5.4)
      </Title>
      <Text c="dimmed" size="sm" mb="md">
        Баланс компании: {balance != null ? `${balance} ₽` : '—'}
      </Text>
      <Stack maw={520} gap="md">
        <NumberInput
          label="Лимит одновременных заказов (по умолчанию)"
          description="1–20; индивидуальные лимиты сотрудника имеют приоритет"
          min={1}
          max={20}
          value={policies.default_max_concurrent_orders}
          onChange={(v) =>
            setPolicies((p) => ({
              ...p,
              default_max_concurrent_orders: typeof v === 'number' ? v : 5,
            }))
          }
        />
        <Checkbox
          label="Без месячного лимита расходов"
          checked={noMonthlyLimit}
          onChange={(e) => setNoMonthlyLimit(e.currentTarget.checked)}
        />
        {!noMonthlyLimit && (
          <NumberInput
            label="Месячный лимит расходов (₽)"
            min={0}
            value={policies.default_monthly_spending_limit ?? 0}
            onChange={(v) =>
              setPolicies((p) => ({
                ...p,
                default_monthly_spending_limit: typeof v === 'number' ? v : 0,
              }))
            }
          />
        )}
        <MultiSelect
          label="Разрешённые категории"
          data={categories.map((c) => ({ value: c, label: c }))}
          value={policies.default_allowed_categories}
          onChange={(v) => setPolicies((p) => ({ ...p, default_allowed_categories: v }))}
          searchable
        />
        <Switch
          label="Photographer может скачивать модели"
          checked={policies.allow_photographer_download}
          onChange={(e) =>
            setPolicies((p) => ({
              ...p,
              allow_photographer_download: e.currentTarget.checked,
            }))
          }
        />
        <Switch
          label="Photographer может добавлять ссылки публикации"
          checked={policies.allow_photographer_add_links}
          onChange={(e) =>
            setPolicies((p) => ({
              ...p,
              allow_photographer_add_links: e.currentTarget.checked,
            }))
          }
        />
        <Switch
          label="Требовать 2FA для всех сотрудников"
          checked={policies.require_2fa_for_all}
          onChange={(e) =>
            setPolicies((p) => ({ ...p, require_2fa_for_all: e.currentTarget.checked }))
          }
        />
        <NumberInput
          label="Авто-блокировка при неактивности (дней)"
          min={1}
          max={3650}
          value={policies.auto_block_inactive_days}
          onChange={(v) =>
            setPolicies((p) => ({
              ...p,
              auto_block_inactive_days: typeof v === 'number' ? v : 90,
            }))
          }
        />
        <NumberInput
          label="Порог низкого баланса (₽)"
          description="Webhook balance.low"
          min={0}
          value={policies.low_balance_threshold}
          onChange={(v) =>
            setPolicies((p) => ({
              ...p,
              low_balance_threshold: typeof v === 'number' ? v : 5000,
            }))
          }
        />
        <Divider label="Уведомления Owner (§3.19)" labelPosition="left" />
        <Text size="sm" c="dimmed">
          Кому слать push/email по событиям компании
        </Text>
        {Object.keys(ROUTING_DEFAULT).map((event) => (
          <Select
            key={event}
            label={EVENT_LABELS[event] || event}
            data={AUDIENCE_OPTIONS}
            value={routing[event] || ROUTING_DEFAULT[event]}
            allowDeselect={false}
            onChange={(v) =>
              setRouting((r) => ({
                ...r,
                [event]: v || ROUTING_DEFAULT[event],
              }))
            }
          />
        ))}
        <Button w="fit-content" loading={saving} onClick={save}>
          Сохранить
        </Button>
      </Stack>
    </SellerShell>
  );
}
