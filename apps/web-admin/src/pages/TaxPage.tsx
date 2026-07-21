import { Button, Group, NumberInput, Select, Stack, TextInput, Textarea } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';
import { PageHeader } from '../components/Panel';
import { api, getApiError } from '../services/api';

type TaxSettings = {
  mode: string;
  full_name?: string;
  inn?: string;
  phone?: string;
  ogrnip?: string;
  ogrn?: string;
  kpp?: string;
  org_name?: string;
  legal_address?: string;
  bank_name?: string;
  bank_bik?: string;
  bank_account?: string;
  vat_rate?: number;
};

export default function TaxPage() {
  const [s, setS] = useState<TaxSettings>({ mode: 'self_employed', vat_rate: 0 });
  const [saving, setSaving] = useState(false);
  const [orderId, setOrderId] = useState('');

  useEffect(() => {
    api
      .get<TaxSettings>('/admin/tax/settings')
      .then(({ data }) => setS(data))
      .catch((e) => notifications.show({ color: 'red', message: getApiError(e) }));
  }, []);

  async function save() {
    setSaving(true);
    try {
      const { data } = await api.put<TaxSettings>('/admin/tax/settings', s);
      setS(data);
      notifications.show({ color: 'teal', message: 'Сохранено' });
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setSaving(false);
    }
  }

  async function exportXlsx() {
    try {
      const { data } = await api.get('/admin/tax/transactions/export', { responseType: 'blob' });
      const url = URL.createObjectURL(data);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'transactions.xlsx';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  async function downloadPdf(kind: 'invoice' | 'act') {
    const id = Number(orderId);
    if (!id) return notifications.show({ color: 'red', message: 'Укажите order_id' });
    try {
      const { data } = await api.post<Blob>(`/admin/tax/${kind}/${id}`, null, { responseType: 'blob' });
      const url = URL.createObjectURL(data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${kind}-${id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  return (
    <>
      <PageHeader
        title="Налоговый модуль"
        description="Самозанятый / ИП / ООО — реквизиты, PDF, Excel"
        action={
          <Button variant="light" onClick={exportXlsx}>
            Excel транзакций
          </Button>
        }
      />
      <Stack maw={640}>
        <Select
          label="Режим"
          value={s.mode}
          onChange={(v) => setS((p) => ({ ...p, mode: v || 'self_employed' }))}
          data={[
            { value: 'self_employed', label: 'Самозанятый (НПД)' },
            { value: 'ip', label: 'ИП' },
            { value: 'ooo', label: 'ООО' },
          ]}
        />
        <TextInput
          label="ФИО / контакт"
          value={s.full_name || ''}
          onChange={(e) => setS((p) => ({ ...p, full_name: e.currentTarget.value }))}
        />
        {s.mode === 'ooo' && (
          <TextInput
            label="Наименование ООО"
            value={s.org_name || ''}
            onChange={(e) => setS((p) => ({ ...p, org_name: e.currentTarget.value }))}
          />
        )}
        <Group grow>
          <TextInput label="ИНН" value={s.inn || ''} onChange={(e) => setS((p) => ({ ...p, inn: e.currentTarget.value }))} />
          <TextInput
            label="Телефон"
            value={s.phone || ''}
            onChange={(e) => setS((p) => ({ ...p, phone: e.currentTarget.value }))}
          />
        </Group>
        {s.mode === 'ip' && (
          <TextInput
            label="ОГРНИП"
            value={s.ogrnip || ''}
            onChange={(e) => setS((p) => ({ ...p, ogrnip: e.currentTarget.value }))}
          />
        )}
        {s.mode === 'ooo' && (
          <Group grow>
            <TextInput label="КПП" value={s.kpp || ''} onChange={(e) => setS((p) => ({ ...p, kpp: e.currentTarget.value }))} />
            <TextInput label="ОГРН" value={s.ogrn || ''} onChange={(e) => setS((p) => ({ ...p, ogrn: e.currentTarget.value }))} />
          </Group>
        )}
        <Textarea
          label="Юр. адрес"
          value={s.legal_address || ''}
          onChange={(e) => setS((p) => ({ ...p, legal_address: e.currentTarget.value }))}
        />
        <Group grow>
          <TextInput
            label="Банк"
            value={s.bank_name || ''}
            onChange={(e) => setS((p) => ({ ...p, bank_name: e.currentTarget.value }))}
          />
          <TextInput
            label="БИК"
            value={s.bank_bik || ''}
            onChange={(e) => setS((p) => ({ ...p, bank_bik: e.currentTarget.value }))}
          />
        </Group>
        <TextInput
          label="Р/с"
          value={s.bank_account || ''}
          onChange={(e) => setS((p) => ({ ...p, bank_account: e.currentTarget.value }))}
        />
        {s.mode !== 'self_employed' && (
          <NumberInput
            label="НДС %"
            value={s.vat_rate ?? 0}
            onChange={(v) => setS((p) => ({ ...p, vat_rate: Number(v) || 0 }))}
            min={0}
            max={20}
          />
        )}
        <Button loading={saving} onClick={save} w="fit-content">
          Сохранить реквизиты
        </Button>
        <Group align="flex-end">
          <TextInput
            label="Order ID"
            placeholder="123"
            value={orderId}
            onChange={(e) => setOrderId(e.currentTarget.value)}
            maw={160}
          />
          <Button variant="light" onClick={() => void downloadPdf('invoice')}>
            PDF счёт
          </Button>
          <Button variant="light" onClick={() => void downloadPdf('act')}>
            PDF акт
          </Button>
        </Group>
      </Stack>
    </>
  );
}
