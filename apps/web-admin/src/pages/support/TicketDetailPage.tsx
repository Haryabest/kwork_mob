import { Button, Card, Grid, Group, Stack, Text, Textarea, Title, Loader, Center, Badge, Paper } from '@mantine/core';
import { IconRobot } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api, getApiError } from '../../services/api';

type Msg = { id: number; body: string; is_staff: boolean; created_at?: string | null };

type TicketUser = {
  id: number;
  email?: string | null;
  full_name?: string | null;
  account_type?: string;
  status?: string;
  orders_count?: number;
  created_at?: string | null;
};

export default function TicketDetailPage() {
  const { id } = useParams();
  const [reply, setReply] = useState('');
  const [suggestion, setSuggestion] = useState('');
  const [status, setStatus] = useState('');
  const [subject, setSubject] = useState('');
  const [category, setCategory] = useState('');
  const [userInfo, setUserInfo] = useState<TicketUser | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    const { data } = await api.get<{
      status: string;
      subject?: string;
      category?: string;
      messages: Msg[];
      user?: TicketUser;
    }>(`/support/questions/${id}`);
    setStatus(data.status);
    setSubject(data.subject || '');
    setCategory(data.category || '');
    setUserInfo(data.user ?? null);
    setMessages(data.messages ?? []);
  }, [id]);

  useEffect(() => {
    load()
      .catch((e) => notifications.show({ color: 'red', message: getApiError(e) }))
      .finally(() => setLoading(false));
  }, [load]);

  async function send() {
    if (!reply.trim()) return;
    setSending(true);
    try {
      await api.post(`/admin/support/questions/${id}/reply`, { message: reply.trim() });
      setReply('');
      setSuggestion('');
      await load();
      notifications.show({ color: 'green', message: 'Ответ отправлен' });
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setSending(false);
    }
  }

  async function escalate() {
    try {
      await api.patch(`/admin/support/questions/${id}/escalate`);
      await load();
      notifications.show({ color: 'orange', message: 'Обращение эскалировано' });
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  if (loading) return <Center py="xl"><Loader color="brand" /></Center>;

  return (
  <Grid gutter="lg">
    <Grid.Col span={{ base: 12, md: 8 }}>
      <Group gap="sm" mb="xs">
        <Title order={2}>Обращение #{id}</Title>
        <Badge variant="light">{status}</Badge>
        {category && <Badge variant="outline">{category}</Badge>}
      </Group>
      {subject && (
        <Text fw={600} mb="sm">
          {subject}
        </Text>
      )}
      <Card withBorder radius="md" padding="lg">
        <Stack>
          {messages.map((m) => (
            <Paper key={m.id} p="sm" bg={m.is_staff ? 'brand.0' : 'gray.0'} radius="md">
              <Text size="xs" c="dimmed" mb={4}>
                {m.is_staff ? 'Сотрудник' : 'Пользователь'}
                {m.created_at ? ` · ${new Date(m.created_at).toLocaleString('ru-RU')}` : ''}
              </Text>
              <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>
                {m.body}
              </Text>
            </Paper>
          ))}
          {suggestion && (
            <Card withBorder bg="brand.0">
              <Text size="sm">{suggestion}</Text>
            </Card>
          )}
          <Textarea
            placeholder="Ответ пользователю…"
            minRows={3}
            value={reply}
            onChange={(event) => setReply(event.currentTarget.value)}
          />
          <Group>
            <Button
              leftSection={<IconRobot size={16} />}
              variant="light"
              onClick={async () => {
                try {
                  const { data } = await api.post<{ suggestion: string }>(
                    `/admin/support/questions/${id}/ai-suggest`,
                  );
                  const text = data.suggestion || '';
                  setSuggestion(text);
                  if (text && !reply.trim()) setReply(text);
                  notifications.show({
                    color: text ? 'teal' : 'yellow',
                    message: text ? 'Черновик ИИ готов' : 'Пустой ответ ИИ',
                  });
                } catch (e) {
                  notifications.show({ color: 'red', message: getApiError(e) });
                }
              }}
            >
              Предложить ответ ИИ
            </Button>
            <Button loading={sending} disabled={!reply.trim()} onClick={send}>
              Отправить ответ
            </Button>
            <Button variant="light" color="orange" onClick={() => void escalate()}>
              Эскалировать
            </Button>
          </Group>
        </Stack>
      </Card>
    </Grid.Col>
    <Grid.Col span={{ base: 12, md: 4 }}>
      <Card withBorder radius="md" padding="lg">
        <Text fw={600} mb="sm">
          Пользователь
        </Text>
        {userInfo ? (
          <Stack gap={6}>
            <Text size="sm">#{userInfo.id}</Text>
            <Text size="sm">{userInfo.full_name || '—'}</Text>
            <Text size="sm" c="dimmed">
              {userInfo.email}
            </Text>
            <Text size="xs" c="dimmed">
              {userInfo.account_type} · {userInfo.status}
            </Text>
            <Text size="xs">Заказов: {userInfo.orders_count ?? 0}</Text>
            {userInfo.created_at && (
              <Text size="xs" c="dimmed">
                Регистрация: {new Date(userInfo.created_at).toLocaleDateString('ru-RU')}
              </Text>
            )}
          </Stack>
        ) : (
          <Text size="sm" c="dimmed">
            Нет данных
          </Text>
        )}
      </Card>
    </Grid.Col>
  </Grid>
  );
}
