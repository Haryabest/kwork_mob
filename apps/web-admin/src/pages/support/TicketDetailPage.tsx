import { Button, Card, Group, Stack, Text, Textarea, Title, Loader, Center, Badge, Paper } from '@mantine/core';
import { IconRobot } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api, getApiError } from '../../services/api';

type Msg = { id: number; body: string; is_staff: boolean; created_at?: string | null };

export default function TicketDetailPage() {
  const { id } = useParams();
  const [reply, setReply] = useState('');
  const [suggestion, setSuggestion] = useState('');
  const [status, setStatus] = useState('');
  const [messages, setMessages] = useState<Msg[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    const { data } = await api.get<{ status: string; messages: Msg[] }>(`/support/questions/${id}`);
    setStatus(data.status);
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

  if (loading) return <Center py="xl"><Loader color="brand" /></Center>;

  return (
    <>
      <Group gap="sm" mb="xs">
        <Title order={2}>Обращение #{id}</Title>
        <Badge variant="light">{status}</Badge>
      </Group>
      <Text c="dimmed" size="sm" mb="lg">
        Чат + «Предложить ответ ИИ»
      </Text>
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
          </Group>
        </Stack>
      </Card>
    </>
  );
}
