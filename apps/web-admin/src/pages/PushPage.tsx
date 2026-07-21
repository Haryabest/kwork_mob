import { Badge, Button, Center, Group, Select, Stack, TextInput, Textarea } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconRefresh } from '@tabler/icons-react';
import { useCallback, useEffect, useState } from 'react';
import { PageHeader, ShellTable } from '../components/Panel';
import { api, getApiError } from '../services/api';

const SEGMENTS = [
  { value: '{}', label: 'Все с marketing_opt_in' },
  { value: '{"account_type":"individual"}', label: 'Физлица' },
  { value: '{"has_orders":true}', label: 'С заказами' },
];

type PushRow = {
  id: number;
  title: string;
  status: string;
  stats?: { reach?: number; pushed?: number; emailed?: number; scheduled_at?: string };
  scheduled_at?: string | null;
  sent_at?: string | null;
  created_at?: string | null;
};

export default function PushPage() {
  const [segment, setSegment] = useState<string | null>(SEGMENTS[0].value);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [sendAt, setSendAt] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [testUserId, setTestUserId] = useState('');
  const [history, setHistory] = useState<PushRow[]>([]);

  const loadHistory = useCallback(async () => {
    try {
      const { data } = await api.get<{ items: PushRow[] }>('/admin/campaigns/push');
      setHistory(data.items ?? []);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }, []);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  async function send(scheduled: boolean) {
    setBusy(true);
    setResult(null);
    try {
      const payload: {
        title: string;
        body: string;
        segment: Record<string, unknown>;
        send_at?: string;
      } = {
        title,
        body,
        segment: JSON.parse(segment || '{}'),
      };
      if (scheduled && sendAt) {
        payload.send_at = new Date(sendAt).toISOString();
      }
      const { data } = await api.post<{ id: number; status: string; stats?: PushRow['stats'] }>(
        '/admin/campaigns/push',
        payload,
      );
      setResult(
        scheduled
          ? `Запланировано #${data.id} (${data.status})`
          : `Рассылка #${data.id}: pushed=${data.stats?.pushed ?? 0}, emailed=${data.stats?.emailed ?? 0}`,
      );
      notifications.show({ color: 'teal', message: scheduled ? 'Push запланирован' : 'Рассылка отправлена' });
      await loadHistory();
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
      <PageHeader
        title="Push-рассылки"
        description="FCM §3.4.3 + email fallback · расписание · журнал"
        action={
          <Button leftSection={<IconRefresh size={16} />} variant="light" onClick={() => void loadHistory()}>
            Обновить журнал
          </Button>
        }
      />
      <Stack maw={560} mb="xl">
        <Select label="Сегмент" value={segment} onChange={setSegment} data={SEGMENTS} />
        <TextInput label="Заголовок" value={title} onChange={(e) => setTitle(e.currentTarget.value)} />
        <Textarea label="Текст" minRows={4} value={body} onChange={(e) => setBody(e.currentTarget.value)} />
        <TextInput
          type="datetime-local"
          label="Отправить в (опц.)"
          value={sendAt}
          onChange={(e) => setSendAt(e.currentTarget.value)}
        />
        <TextInput
          label="E2E user_id (опц.)"
          placeholder="пусто = текущий staff"
          value={testUserId}
          onChange={(e) => setTestUserId(e.currentTarget.value)}
        />
        <Group>
          <Button loading={busy} onClick={() => void send(false)} disabled={!title || !body}>
            Отправить сейчас
          </Button>
          <Button loading={busy} variant="light" onClick={() => void send(true)} disabled={!title || !body || !sendAt}>
            Запланировать
          </Button>
          <Button loading={busy} variant="light" onClick={() => void sendTest()}>
            Push E2E тест
          </Button>
        </Group>
        {result && <Center>{result}</Center>}
      </Stack>

      <ShellTable
        headers={['ID', 'Заголовок', 'Статус', 'Reach', 'Когда']}
        rows={history.map((h) => [
          String(h.id),
          h.title,
          <Badge key={h.id} color={h.status === 'sent' ? 'teal' : h.status === 'scheduled' ? 'blue' : 'gray'} variant="light">
            {h.status}
          </Badge>,
          String(h.stats?.reach ?? '—'),
          h.sent_at
            ? new Date(h.sent_at).toLocaleString('ru-RU')
            : h.scheduled_at
              ? `⏱ ${new Date(h.scheduled_at).toLocaleString('ru-RU')}`
              : h.created_at
                ? new Date(h.created_at).toLocaleString('ru-RU')
                : '—',
        ])}
      />
    </>
  );
}
