import { Button, Center, Group, Select, Stack, TextInput, Textarea } from '@mantine/core';
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
  const [testUserId, setTestUserId] = useState('');

  async function send() {
    setBusy(true);
    setResult(null);
    try {
      const { data } = await api.post<{ id: number; stats?: { reach?: number; sent?: number; pushed?: number; emailed?: number } }>(
        '/admin/campaigns/push',
        {
          title,
          body,
          segment: JSON.parse(segment || '{}'),
        },
      );
      setResult(
        `Рассылка #${data.id}: reach=${data.stats?.reach ?? 0}, pushed=${data.stats?.pushed ?? 0}, emailed=${data.stats?.emailed ?? 0}`,
      );
      notifications.show({ color: 'teal', message: 'Рассылка отправлена (FCM + email fallback)' });
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setBusy(false);
    }
  }

  async function sendTest() {
    setBusy(true);
    try {
      const payload: { title: string; body: string; user_id?: number } = {
        title: title || 'KWork Mob test',
        body: body || 'Push E2E OK',
      };
      if (testUserId) payload.user_id = Number(testUserId);
      const { data } = await api.post<{
        delivered_push: boolean;
        email_fallback: boolean;
        devices: number;
        fcm_configured: boolean;
      }>('/admin/campaigns/push/test', payload);
      setResult(
        `E2E: devices=${data.devices}, fcm=${data.fcm_configured}, push=${data.delivered_push}, email=${data.email_fallback}`,
      );
      notifications.show({
        color: data.delivered_push || data.email_fallback ? 'teal' : 'orange',
        message: data.delivered_push ? 'Push доставлен' : data.email_fallback ? 'Email fallback' : 'Нет доставки',
      });
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="Push-рассылки" description="FCM §3.4.3 + email fallback · E2E /push/test" />
      <Stack maw={560}>
        <Select label="Сегмент" value={segment} onChange={setSegment} data={SEGMENTS} />
        <TextInput label="Заголовок" value={title} onChange={(e) => setTitle(e.currentTarget.value)} />
        <Textarea label="Текст" minRows={4} value={body} onChange={(e) => setBody(e.currentTarget.value)} />
        <TextInput
          label="E2E user_id (опц.)"
          placeholder="пусто = текущий staff"
          value={testUserId}
          onChange={(e) => setTestUserId(e.currentTarget.value)}
        />
        <Group>
          <Button loading={busy} onClick={send} disabled={!title || !body}>
            Отправить сегменту
          </Button>
          <Button loading={busy} variant="light" onClick={sendTest}>
            Push E2E тест
          </Button>
        </Group>
        {result && <Center>{result}</Center>}
      </Stack>
    </>
  );
}
