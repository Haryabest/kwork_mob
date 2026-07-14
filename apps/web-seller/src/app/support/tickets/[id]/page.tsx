'use client';

import { ActionIcon, Badge, Button, Card, Group, Stack, Text, Textarea, Paper, Anchor } from '@mantine/core';
import { IconSend } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { SellerShell } from '../../../../components/SellerShell';
import { PageHeader } from '../../../../components/ui';
import { api, apiMessage } from '../../../../services/api';

type Msg = { id: number; body: string; is_staff: boolean; created_at?: string | null };

const STATUS_LABEL: Record<string, string> = {
  new: 'Новое',
  in_progress: 'В работе',
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
  const [attachments, setAttachments] = useState<string[]>([]);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);

  const closed = status === 'closed' || status === 'resolved';

  const load = useCallback(async () => {
    const { data } = await api.get<{
      status: string;
      subject?: string;
      attachments?: string[];
      messages: Msg[];
    }>(`/support/questions/${id}`);
    setStatus(data.status);
    setSubject(data.subject || `Обращение #${id}`);
    setAttachments(data.attachments ?? []);
    setMessages(data.messages ?? []);
  }, [id]);

  useEffect(() => {
    load().catch((error) => notifications.show({ color: 'red', message: apiMessage(error) }));
  }, [load]);

  async function send() {
    if (!text.trim() || closed) return;
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

  async function closeTicket() {
    try {
      await api.post(`/support/questions/${id}/close`);
      await load();
      notifications.show({ color: 'teal', message: 'Обращение закрыто' });
    } catch (error) {
      notifications.show({ color: 'red', message: apiMessage(error) });
    }
  }

  return (
    <SellerShell>
      <PageHeader
        title={subject}
        description={`Обращение #${id}`}
        action={
          <Group gap="sm">
            <Badge variant="light">{STATUS_LABEL[status] ?? status}</Badge>
            {!closed && (
              <Button variant="light" color="gray" onClick={() => void closeTicket()}>
                Закрыть
              </Button>
            )}
            <Button component={Link} href="/support" variant="default">
              К списку
            </Button>
          </Group>
        }
      />
      <Stack gap="lg">
        {attachments.length > 0 && (
          <Card withBorder>
            <Text fw={600} mb="xs">
              Вложения
            </Text>
            <Stack gap={4}>
              {attachments.map((url) => (
                <Anchor key={url} href={url} target="_blank" rel="noreferrer" size="sm">
                  {url.split('/').pop() || url}
                </Anchor>
              ))}
            </Stack>
          </Card>
        )}
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
            {!closed ? (
              <Group align="end">
                <Textarea
                  placeholder="Уточняющий вопрос…"
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
                  onClick={() => void send()}
                  disabled={!text.trim()}
                >
                  <IconSend size={18} />
                </ActionIcon>
              </Group>
            ) : (
              <Text size="sm" c="dimmed">
                Обращение закрыто — новые сообщения недоступны
              </Text>
            )}
          </Stack>
        </Card>
      </Stack>
    </SellerShell>
  );
}
