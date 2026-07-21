import { useCallback, useEffect, useState } from 'react';
import { Center, Loader } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { PageHeader, ShellTable } from '../components/Panel';
import { api, getApiError } from '../services/api';

type Row = {
  company_id: number;
  company_name?: string;
  active_keys: number;
  used_keys_7d: number;
  orders_7d: number;
  revenue_7d_rub: number;
  last_used_at?: string;
};

export default function B2bApiUsagePage() {
  const [items, setItems] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<{ items: Row[] }>('/admin/b2b/api-usage', { params: { days: 7 } });
      setItems(data.items ?? []);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  return (
    <>
      <PageHeader title="B2B API usage" description="Использование API-ключей §11.5" />
      <ShellTable
        headers={['Компания', 'Ключи', 'Used 7д', 'Заказы 7д', 'Выручка', 'Last used']}
        rows={items.map((r) => [
          r.company_name || `#${r.company_id}`,
          String(r.active_keys),
          String(r.used_keys_7d),
          String(r.orders_7d),
          String(r.revenue_7d_rub),
          r.last_used_at ?? '—',
        ])}
      />
    </>
  );
}
