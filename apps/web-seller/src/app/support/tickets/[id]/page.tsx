'use client';

import { ActionIcon, Badge, Card, Group, Stack, Text, Textarea, Title, Paper } from '@mantine/core';
import { IconSend } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { SellerShell } from '../../../../components/SellerShell';
import { api, apiMessage } from '../../../../services/api';

type Msg = { id: number; body: string; is_staff: boolean; created_at?: string | null };

const STATUS_LABEL: Record<string, string> = {
  new: 'Новое',
  answered: 'Отвечено',
  waiting_user: 'Ожидает вас',
  closed: 'Закрыто',
  resolved: 'Решено',
};

export default function TicketPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const [status, setStatus] = useState('');
  const [subject, setSubject] = useState('');
  const [messages, setMessages] = useState<Msg[]>([]);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    const { data } = await api.get<{
      status: string;
      subject?: string;
      messages: Msg[];
    }>(`/support/questions/${id}`);
    setStatus(data.status);
    setSubject(data.subject || `Обращение #${id}`);
    setMessages(data.messages ?? []);
  }, [id]);

  useEffect(() => {
    load().catch((error) => notifications.show({ color: 'red', message: apiMessage(error) }));
  }, [load]);

  async function send() {
    if (!text.trim()) return;
    setSending(true);
    try {
      await api.post(`/support/questions/${id}/messages`, { message: text.trim() });
      setText('');
      await load();
    } catch (error) {
      notifications.show({ color: 'red', message: apiMessage(error) });
    } finally {
      setSending(false);
    }
  }

  return (
    <SellerShell>
      <Stack gap="lg">
        <div>
          <Group gap="sm">
            <Title order={2}>{subject}</Title>
            <Badge variant="light">{STATUS_LABEL[status] ?? status}</Badge>
          </Group>
          <Text size="sm" c="dimmed">
            Обращение #{id}
          </Text>
        </div>
        <Card withBorder mih={380}>
          <Stack justify="space-between" h="100%" gap="md">
            <Stack gap="sm">
              {messages.length === 0 ? (
                <Text c="dimmed" ta="center" py="xl">
                  Сообщений пока нет
                </Text>
              ) : (
                messages.map((m) => (
                  <Paper
                    key={m.id}
                    p="sm"
                    radius="md"
                    bg={m.is_staff ? 'brand.0' : 'gray.0'}
                    style={{ alignSelf: m.is_staff ? 'flex-start' : 'flex-end', maxWidth: '85%' }}
                  >
                    <Text size="xs" c="dimmed" mb={4}>
                      {m.is_staff ? 'Поддержка' : 'Вы'}
                      {m.created_at ? ` · ${new Date(m.created_at).toLocaleString('ru-RU')}` : ''}
                    </Text>
                    <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>
                      {m.body}
                    </Text>
                  </Paper>
                ))
              )}
            </Stack>
            <Group align="end">
              <Textarea
                placeholder="Введите сообщение"
                autosize
                minRows={2}
                style={{ flex: 1 }}
                value={text}
                onChange={(e) => setText(e.currentTarget.value)}
              />
              <ActionIcon
                size="lg"
                color="brand"
                aria-label="Отправить"
                loading={sending}
                onClick={send}
                disabled={!text.trim()}
              >
                <IconSend size={18} />
              </ActionIcon>
            </Group>
          </Stack>
        </Card>
      </Stack>
    </SellerShell>
  );
}
