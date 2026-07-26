'use client';

import { ActionIcon, Badge, Button, Group, Paper, Stack, Text, Textarea } from '@mantine/core';
import { IconSend } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { SellerShell } from '../../../../components/SellerShell';
import { PageHeader, Surface } from '../../../../components/ui';
import { api, apiMessage } from '../../../../services/api';

type Msg = { id: number; body: string; is_staff: boolean; created_at?: string | null };

import { supportStatusLabel } from '../../../../lib/supportStatus';
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
            <Badge variant="light">{supportStatusLabel(status)}</Badge>
            {!closed && (
              <Button variant="light" color="gray" onClick={() => void closeTicket()}>
                Закрыть
              </Button>
            )}
            <Button component={Link} href="/support" variant="default">
              К поддержке
            </Button>
          </Group>
        }
      />

      <div
        style={{
          display: 'grid',
          gap: '1.25rem',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        }}
      >
        <Surface>
          <Stack gap="md" mih={420}>
            {messages.length === 0 ? (
              <Text c="dimmed" ta="center" py="xl">
                Сообщений пока нет
              </Text>
            ) : (
              messages.map((m) => (
                <Paper
                  key={m.id}
                  p="md"
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
            {!closed ? (
              <Group align="flex-end" mt="auto" pt="md">
                <Textarea
                  placeholder="Уточняющий вопрос…"
                  autosize
                  minRows={3}
                  style={{ flex: 1 }}
                  value={text}
                  onChange={(e) => setText(e.currentTarget.value)}
                />
                <ActionIcon
                  size="xl"
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
              <Text size="sm" c="dimmed" mt="auto">
                Обращение закрыто — новые сообщения недоступны
              </Text>
            )}
          </Stack>
        </Surface>

        <Surface>
          <Stack gap="sm">
            <Text fw={600}>Детали</Text>
            <Text size="sm" c="#6d6c77">
              Статус: {supportStatusLabel(status)}
            </Text>
            {attachments.length > 0 && (
              <>
                <Text fw={600} mt="sm">
                  Вложения
                </Text>
                {attachments.map((url) => (
                  <Text key={url} component="a" href={url} target="_blank" rel="noreferrer" size="sm" c="brand">
                    {url.split('/').pop() || url}
                  </Text>
                ))}
              </>
            )}
          </Stack>
        </Surface>
      </div>
    </SellerShell>
  );
}
