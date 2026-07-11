'use client';

import {
  Accordion,
  Button,
  Card,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
  Badge,
  Group,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import Link from 'next/link';
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { SellerShell } from '../../components/SellerShell';
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
      notifications.show({ color: 'green', message: 'Вопрос отправлен. Ответ придёт в кабинет и на email.' });
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
      <Title order={2} mb="xs">
        Поддержка
      </Title>
      <Text c="dimmed" size="sm" mb="lg">
        FAQ и обращения
      </Text>
      <Stack gap="lg">
        <Card withBorder>
          <Group justify="space-between" mb="md">
            <Title order={3}>Частые вопросы</Title>
            <TextInput
              placeholder="Поиск по FAQ"
              value={search}
              onChange={(e) => setSearch(e.currentTarget.value)}
              maw={260}
            />
          </Group>
          {filteredFaq.length === 0 ? (
            <Text c="dimmed">FAQ пока пуст</Text>
          ) : (
            <Accordion>
              {filteredFaq.map((item) => (
                <Accordion.Item key={item.id} value={String(item.id)}>
                  <Accordion.Control>
                    <Text size="sm" c="dimmed" span>
                      {item.category} ·{' '}
                    </Text>
                    {item.question}
                  </Accordion.Control>
                  <Accordion.Panel>{item.answer}</Accordion.Panel>
                </Accordion.Item>
              ))}
            </Accordion>
          )}
          <Text size="sm" c="dimmed" mt="md">
            Не нашли ответ? Задайте вопрос ниже.
          </Text>
        </Card>

        <Card withBorder>
          <Title order={3} mb="md">
            Новое обращение
          </Title>
          <Stack maw={640}>
            <TextInput label="Тема" required value={subject} onChange={(e) => setSubject(e.currentTarget.value)} />
            <Select
              label="Категория"
              data={['Заказ', 'Оплата', 'Модель', 'Другое']}
              value={category}
              onChange={setCategory}
            />
            <Textarea
              label="Сообщение"
              minRows={4}
              required
              value={message}
              onChange={(e) => setMessage(e.currentTarget.value)}
            />
            <Button w="fit-content" loading={loading} onClick={submitTicket}>
              Отправить
            </Button>
          </Stack>
        </Card>

        <Card withBorder>
          <Title order={3} mb="md">
            Мои обращения
          </Title>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Тема</Table.Th>
                <Table.Th>Создано</Table.Th>
                <Table.Th>Статус</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {tickets.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={3}>
                    <Text c="dimmed" ta="center" py="lg">
                      Обращений пока нет
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                tickets.map((t) => (
                  <Table.Tr key={t.id}>
                    <Table.Td>
                      <AnchorLike href={`/support/tickets/${t.id}`}>{t.subject || t.message.slice(0, 60)}</AnchorLike>
                    </Table.Td>
                    <Table.Td>{t.created_at ? new Date(t.created_at).toLocaleString('ru-RU') : '—'}</Table.Td>
                    <Table.Td>
                      <Badge variant="light">{STATUS_LABEL[t.status] ?? t.status}</Badge>
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Card>
      </Stack>
    </SellerShell>
  );
}

function AnchorLike({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Text component={Link} href={href} c="brand" fw={500} style={{ textDecoration: 'none' }}>
      {children}
    </Text>
  );
}
