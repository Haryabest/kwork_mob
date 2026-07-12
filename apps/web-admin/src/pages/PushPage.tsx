import { Button, Center, Loader, Select, Stack, TextInput, Textarea } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useState } from 'react';
import { PageHeader } from '../components/Panel';
import { api, getApiError } from '../services/api';

const SEGMENTS = [
  { value: '{}', label: 'Все с marketing_opt_in' },
  { value: '{"account_type":"individual"}', label: 'Физлица' },
  { value: '{"has_orders":true}', label: 'С заказами' },
];

export default function PushPage() {
  const [segment, setSegment] = useState<string | null>(SEGMENTS[0].value);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function send() {
    setBusy(true);
    setResult(null);
    try {
      const { data } = await api.post<{ id: number; stats?: { reach?: number; sent?: number } }>(
        '/admin/campaigns/push',
        {
          title,
          body,
          segment: JSON.parse(segment || '{}'),
        },
      );
      setResult(`Рассылка #${data.id}: reach=${data.stats?.reach ?? 0}, sent=${data.stats?.sent ?? 0}`);
      notifications.show({ color: 'teal', message: 'Рассылка отправлена (email fallback)' });
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="Push-рассылки" description="Сегментация + email fallback при отсутствии FCM" />
      <Stack maw={560}>
        <Select label="Сегмент" value={segment} onChange={setSegment} data={SEGMENTS} />
        <TextInput label="Заголовок" value={title} onChange={(e) => setTitle(e.currentTarget.value)} />
        <Textarea label="Текст" minRows={4} value={body} onChange={(e) => setBody(e.currentTarget.value)} />
        <Button w="fit-content" loading={busy} onClick={send} disabled={!title || !body}>
          Отправить
        </Button>
        {result && <Center>{result}</Center>}
      </Stack>
    </>
  );
}
