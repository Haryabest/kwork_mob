import { Button, Center, Group, Loader, Modal, NumberInput, Select, Stack, TextInput, Text } from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';
import { PageHeader, ShellTable, StateBadge } from '../components/Panel';
import { api, getApiError } from '../services/api';

type Promo = {
  id: number;
  code_prefix?: string;
  name?: string;
  discount_type: string;
  discount_value: number;
  max_uses?: number | null;
  used_count: number;
  expires_at?: string | null;
  is_active: boolean;
  tier?: string | null;
  total_discount?: number;
};

export default function PromocodesPage() {
  const [items, setItems] = useState<Promo[]>([]);
  const [loading, setLoading] = useState(true);
  const [opened, setOpened] = useState(false);
  const [name, setName] = useState('');
  const [discountType, setDiscountType] = useState<string | null>('percent');
  const [discountValue, setDiscountValue] = useState<number | string>(10);
  const [maxUses, setMaxUses] = useState<number | string | undefined>(100);
  const [tier, setTier] = useState<string | null>(null);
  const [plainCode, setPlainCode] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);

  async function load() {
    const { data } = await api.get<{ items: Promo[] }>('/admin/promocodes');
    setItems(data.items ?? []);
  }

  useEffect(() => {
    load()
      .catch((e) => notifications.show({ color: 'red', message: getApiError(e) }))
      .finally(() => setLoading(false));
  }, []);

  async function create() {
    try {
      const { data } = await api.post<{ code: string }>('/admin/promocodes', {
        name: name || undefined,
        discount_type: discountType,
        discount_value: Number(discountValue),
        max_uses: maxUses === '' || maxUses == null ? null : Number(maxUses),
        tier: tier || null,
      });
      setPlainCode(data.code);
      notifications.show({ color: 'teal', message: 'Промокод создан — скопируйте код сейчас' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  async function deactivate(id: number) {
    try {
      await api.post(`/admin/promocodes/${id}/deactivate`);
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  async function importCsv(file: File) {
    setImporting(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const { data } = await api.post<{ created: Array<{ code: string }>; errors: unknown[] }>(
        '/admin/promocodes/import-csv',
        form,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      );
      notifications.show({
        color: 'teal',
        message: `Импорт: ${data.created?.length ?? 0} промокодов`,
      });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setImporting(false);
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
      <PageHeader
        title="Промокоды"
        description="Хэш в БД, код показывается один раз (§8.5)"
        action={
          <Group>
            <Button component="label" variant="light" loading={importing}>
              Импорт CSV
              <input
                type="file"
                accept=".csv,text/csv"
                hidden
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) void importCsv(f);
                  e.target.value = '';
                }}
              />
            </Button>
            <Button leftSection={<IconPlus size={16} />} onClick={() => { setPlainCode(null); setOpened(true); }}>
              Создать
            </Button>
          </Group>
        }
      />
      <ShellTable
        headers={['Префикс', 'Название', 'Скидка', 'Использовано', 'Тариф', 'Статус', '']}
        rows={
          items.length
            ? items.map((p) => [
                <Text key={`c-${p.id}`} fw={600}>
                  {p.code_prefix}****
                </Text>,
                p.name ?? '—',
                p.discount_type === 'percent' ? `${p.discount_value}%` : `${p.discount_value} ₽`,
                `${p.used_count}${p.max_uses != null ? ` / ${p.max_uses}` : ''}`,
                p.tier ?? 'любой',
                <StateBadge key={`s-${p.id}`} value={p.is_active ? 'Активен' : 'Выкл'} color={p.is_active ? 'teal' : 'gray'} />,
                p.is_active ? (
                  <Button key={`d-${p.id}`} size="xs" variant="light" color="red" onClick={() => void deactivate(p.id)}>
                    Отключить
                  </Button>
                ) : (
                  '—'
                ),
              ])
            : [['—', 'Нет промокодов', '—', '—', '—', '—', '—']]
        }
      />
      <Modal opened={opened} onClose={() => setOpened(false)} title="Новый промокод">
        <Stack>
          <TextInput label="Название" value={name} onChange={(e) => setName(e.currentTarget.value)} />
          <Select
            label="Тип скидки"
            value={discountType}
            onChange={setDiscountType}
            data={[
              { value: 'percent', label: 'Процент' },
              { value: 'fixed', label: 'Фикс, ₽' },
            ]}
          />
          <NumberInput label="Значение" value={discountValue} onChange={setDiscountValue} min={1} />
          <NumberInput label="Лимит использований" value={maxUses} onChange={setMaxUses} min={1} />
          <Select
            label="Тариф"
            clearable
            value={tier}
            onChange={setTier}
            data={[
              { value: 'small', label: 'Малый' },
              { value: 'large', label: 'Крупный' },
            ]}
          />
          {plainCode && (
            <Text fw={700} c="teal">
              Код (один раз): {plainCode}
            </Text>
          )}
          <Group>
            <Button onClick={() => void create()}>Создать</Button>
            <Button variant="light" onClick={() => setOpened(false)}>
              Закрыть
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
