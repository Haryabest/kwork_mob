'use client';

import {
  Accordion,
  Badge,
  Button,
  FileButton,
  Group,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Textarea,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import Link from 'next/link';
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { SellerShell } from '../../components/SellerShell';
import { EmptyState, PageHeader, ScrollTable, Surface } from '../../components/ui';
import { api, apiMessage } from '../../services/api';

type FaqItem = { id: number; category: string; question: string; answer: string };
type Ticket = {
  id: number;
  subject?: string | null;
  category?: string | null;
  message: string;
  status: string;
  attachments?: string[];
  created_at?: string | null;
};

const STATUS_LABEL: Record<string, string> = {
  new: 'Новое',
  in_progress: 'В работе',
  answered: 'Отвечено',
  waiting_user: 'Ожидает вас',
  closed: 'Закрыто',
  resolved: 'Решено',
};

const STATUS_COLOR: Record<string, string> = {
  new: 'blue',
  in_progress: 'yellow',
  answered: 'teal',
  waiting_user: 'orange',
  closed: 'gray',
  resolved: 'gray',
};

export default function SupportPage() {
  const [faq, setFaq] = useState<FaqItem[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [subject, setSubject] = useState('');
  const [category, setCategory] = useState<string | null>('Заказ');
  const [message, setMessage] = useState('');
  const [attachments, setAttachments] = useState<{ key: string; url: string; filename?: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [search, setSearch] = useState('');
  const [tab, setTab] = useState<string | null>('faq');

  async function load() {
    const [faqRes, ticketsRes] = await Promise.all([
      api.get<{ items: FaqItem[] }>('/faq'),
      api.get<{ items: Ticket[] }>('/support/questions'),
    ]);
    setFaq(faqRes.data.items ?? []);
    setTickets(ticketsRes.data.items ?? []);
  }

  useEffect(() => {
    load().catch((error) => notifications.show({ color: 'red', message: apiMessage(error) }));
  }, []);

  const filteredFaq = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return faq;
    return faq.filter(
      (item) =>
        item.question.toLowerCase().includes(q) ||
        item.answer.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q),
    );
  }, [faq, search]);

  async function onFiles(files: File[] | null) {
    if (!files?.length) return;
    if (attachments.length + files.length > 5) {
      return notifications.show({ color: 'red', message: 'Не больше 5 файлов' });
    }
    setUploading(true);
    try {
      const uploaded: { key: string; url: string; filename?: string }[] = [];
      for (const file of files) {
        if (file.size > 5 * 1024 * 1024) {
          notifications.show({ color: 'red', message: `${file.name}: больше 5 МБ` });
          continue;
        }
        const form = new FormData();
        form.append('file', file);
        const { data } = await api.post<{ key: string; url: string; filename?: string }>(
          '/support/attachments',
          form,
        );
        uploaded.push(data);
      }
      setAttachments((prev) => [...prev, ...uploaded]);
    } catch (error) {
      notifications.show({ color: 'red', message: apiMessage(error) });
    } finally {
      setUploading(false);
    }
  }

  async function submitTicket() {
    if (message.trim().length < 10) {
      return notifications.show({ color: 'red', message: 'Сообщение не короче 10 символов' });
    }
    setLoading(true);
    try {
      const { data } = await api.post<{ id: number }>('/support/questions', {
        subject: subject || 'Обращение',
        category,
        message,
        attachments: attachments.map((a) => a.url),
      });
      notifications.show({
        color: 'teal',
        message: 'Ваш вопрос отправлен. Ответ придёт в кабинет и на email.',
      });
      setSubject('');
      setMessage('');
      setAttachments([]);
      await load();
      if (data?.id) {
        window.location.href = `/support/tickets/${data.id}`;
      }
    } catch (error) {
      notifications.show({ color: 'red', message: apiMessage(error) });
    } finally {
      setLoading(false);
    }
  }

  return (
    <SellerShell>
      <PageHeader
        title="Поддержка"
        description="База знаний, новые обращения и история диалогов со службой поддержки"
      />

      <Surface>
        <Tabs value={tab} onChange={setTab}>
          <Tabs.List mb="lg">
            <Tabs.Tab value="faq">Частые вопросы</Tabs.Tab>
            <Tabs.Tab value="new">Новое обращение</Tabs.Tab>
            <Tabs.Tab value="tickets">
              Мои обращения{tickets.length ? ` (${tickets.length})` : ''}
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="faq">
            <Group justify="space-between" mb="md" wrap="wrap">
              <Text size="sm" c="#6d6c77" maw={520}>
                Ответы на популярные вопросы. Не нашли ответ — создайте обращение во вкладке «Новое обращение».
              </Text>
              <TextInput
                placeholder="Поиск по FAQ"
                value={search}
                onChange={(e) => setSearch(e.currentTarget.value)}
                maw={320}
                w="100%"
              />
            </Group>
            {filteredFaq.length === 0 ? (
              <EmptyState title="FAQ пока пуст" hint="Вопросы появятся после публикации в staff-панели" />
            ) : (
              <Accordion variant="separated" radius="md">
                {filteredFaq.map((item) => (
                  <Accordion.Item key={item.id} value={String(item.id)}>
                    <Accordion.Control>
                      <Text size="xs" c="#6d6c77" span>
                        {item.category} ·{' '}
                      </Text>
                      {item.question}
                    </Accordion.Control>
                    <Accordion.Panel>
                      <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>
                        {item.answer}
                      </Text>
                      <Button
                        mt="sm"
                        variant="light"
                        size="xs"
                        onClick={() => {
                          setSubject(item.question.slice(0, 200));
                          setCategory(item.category || 'Другое');
                          setTab('new');
                        }}
                      >
                        Задать вопрос по теме
                      </Button>
                    </Accordion.Panel>
                  </Accordion.Item>
                ))}
              </Accordion>
            )}
          </Tabs.Panel>

          <Tabs.Panel value="new">
            <div
              style={{
                display: 'grid',
                gap: '1.25rem',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              }}
            >
              <Stack gap="md">
                <TextInput
                  label="Тема"
                  required
                  value={subject}
                  onChange={(e) => setSubject(e.currentTarget.value)}
                />
                <TextInput
                  label="Категория"
                  value={category || ''}
                  onChange={(e) => setCategory(e.currentTarget.value || null)}
                />
                <Textarea
                  label="Сообщение"
                  minRows={8}
                  required
                  value={message}
                  onChange={(e) => setMessage(e.currentTarget.value)}
                />
              </Stack>
              <Stack gap="md">
                <Text fw={600}>Вложения</Text>
                <Text size="sm" c="#6d6c77">
                  До 5 файлов, каждый не более 5 МБ. Форматы: JPEG, PNG, PDF.
                </Text>
                <Group>
                  <FileButton onChange={onFiles} accept="image/jpeg,image/png,application/pdf" multiple>
                    {(props) => (
                      <Button {...props} variant="light" loading={uploading}>
                        Прикрепить файлы
                      </Button>
                    )}
                  </FileButton>
                </Group>
                {attachments.length > 0 && (
                  <Stack gap={4}>
                    {attachments.map((a) => (
                      <Text key={a.key} size="sm">
                        {a.filename || a.key}
                      </Text>
                    ))}
                  </Stack>
                )}
                <Button loading={loading} onClick={() => void submitTicket()} w={{ base: '100%', sm: 240 }}>
                  Отправить обращение
                </Button>
              </Stack>
            </div>
          </Tabs.Panel>

          <Tabs.Panel value="tickets">
            {tickets.length === 0 ? (
              <Stack align="center" py="xl" gap="md">
                <EmptyState title="Обращений пока нет" hint="Задайте вопрос во вкладке «Новое обращение»" />
                <Button variant="light" onClick={() => setTab('new')}>
                  Создать обращение
                </Button>
              </Stack>
            ) : (
              <ScrollTable>
                <Table verticalSpacing="md" miw={640}>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Тема</Table.Th>
                      <Table.Th>Категория</Table.Th>
                      <Table.Th>Создано</Table.Th>
                      <Table.Th>Статус</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {tickets.map((t) => (
                      <Table.Tr key={t.id}>
                        <Table.Td>
                          <AnchorLike href={`/support/tickets/${t.id}`}>
                            {t.subject || t.message.slice(0, 60)}
                          </AnchorLike>
                        </Table.Td>
                        <Table.Td>{t.category || '—'}</Table.Td>
                        <Table.Td>{t.created_at ? new Date(t.created_at).toLocaleString('ru-RU') : '—'}</Table.Td>
                        <Table.Td>
                          <Badge variant="light" color={STATUS_COLOR[t.status] ?? 'brand'}>
                            {STATUS_LABEL[t.status] ?? t.status}
                          </Badge>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </ScrollTable>
            )}
          </Tabs.Panel>
        </Tabs>
      </Surface>
    </SellerShell>
  );
}

function AnchorLike({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Text component={Link} href={href} c="brand" fw={600} style={{ textDecoration: 'none' }}>
      {children}
    </Text>
  );
}
