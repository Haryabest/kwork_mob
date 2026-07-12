'use client';

import {
  Accordion,
  Button,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Badge,
  Group,
  Title,
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
  created_at?: string | null;
};

const STATUS_LABEL: Record<string, string> = {
  new: 'Новое',
  answered: 'Отвечено',
  waiting_user: 'Ожидает вас',
  closed: 'Закрыто',
  resolved: 'Решено',
};

/** §20.7 Поддержка и FAQ */
export default function SupportPage() {
  const [faq, setFaq] = useState<FaqItem[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [subject, setSubject] = useState('');
  const [category, setCategory] = useState<string | null>('Заказ');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');

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

  async function submitTicket() {
    if (message.trim().length < 10) {
      return notifications.show({ color: 'red', message: 'Сообщение не короче 10 символов' });
    }
    setLoading(true);
    try {
      await api.post('/support/questions', {
        subject: subject || 'Обращение',
        category,
        message,
      });
      notifications.show({
        color: 'teal',
        message: 'Вопрос отправлен. Ответ придёт в кабинет и на email.',
      });
      setSubject('');
      setMessage('');
      await load();
    } catch (error) {
      notifications.show({ color: 'red', message: apiMessage(error) });
    } finally {
      setLoading(false);
    }
  }

  return (
    <SellerShell>
      <PageHeader title="Поддержка и FAQ" description="База знаний и обращения в службу поддержки" />

      <div
        style={{
          display: 'grid',
          gap: '1.5rem',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        }}
      >
        <Surface style={{ gridColumn: '1 / -1' }}>
          <Group justify="space-between" mb="md" wrap="wrap" gap="md">
            <Title order={4}>Частые вопросы</Title>
            <TextInput
              placeholder="Поиск по FAQ"
              value={search}
              onChange={(e) => setSearch(e.currentTarget.value)}
              maw={280}
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
                  </Accordion.Panel>
                </Accordion.Item>
              ))}
            </Accordion>
          )}
        </Surface>

        <Surface>
          <Title order={4} mb="md">
            Новое обращение
          </Title>
          <Stack>
            <TextInput label="Тема" required value={subject} onChange={(e) => setSubject(e.currentTarget.value)} size="md" />
            <Select
              label="Категория"
              data={['Заказ', 'Оплата', 'Модель', 'Другое']}
              value={category}
              onChange={setCategory}
              size="md"
            />
            <Textarea
              label="Сообщение"
              minRows={4}
              required
              value={message}
              onChange={(e) => setMessage(e.currentTarget.value)}
              size="md"
            />
            <Button w={{ base: '100%', sm: 'fit-content' }} loading={loading} onClick={() => void submitTicket()}>
              Отправить
            </Button>
          </Stack>
        </Surface>

        <Surface>
          <Title order={4} mb="md">
            Мои обращения
          </Title>
          {tickets.length === 0 ? (
            <EmptyState title="Обращений пока нет" hint="Задайте вопрос — ответим в кабинете и на email" />
          ) : (
            <ScrollTable>
              <Table verticalSpacing="md" miw={420}>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Тема</Table.Th>
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
                      <Table.Td>{t.created_at ? new Date(t.created_at).toLocaleString('ru-RU') : '—'}</Table.Td>
                      <Table.Td>
                        <Badge variant="light" color="brand">
                          {STATUS_LABEL[t.status] ?? t.status}
                        </Badge>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </ScrollTable>
          )}
        </Surface>
      </div>
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
