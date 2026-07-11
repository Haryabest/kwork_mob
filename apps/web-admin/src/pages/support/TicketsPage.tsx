import { Badge, Button, Card, Group, Select, Table, Text, TextInput, Title, Loader, Center } from '@mantine/core';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, getApiError } from '../../services/api';
import { notifications } from '@mantine/notifications';

type Ticket = {
  id: number;
  user_email?: string | null;
  subject?: string | null;
  message: string;
  status: string;
  created_at?: string | null;
};

const STATUS: Record<string, string> = {
  new: 'Новое',
  answered: 'Отвечено',
  waiting_user: 'Ожидает пользователя',
  closed: 'Закрыто',
  resolved: 'Решено',
};

export default function TicketsPage() {
  const [items, setItems] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');
  const [status, setStatus] = useState<string | null>('Все');

  useEffect(() => {
    api
      .get<{ items: Ticket[] }>('/admin/support/questions')
      .then(({ data }) => setItems(data.items ?? []))
      .catch((e) => notifications.show({ color: 'red', message: getApiError(e) }))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    return items.filter((t) => {
      if (status && status !== 'Все' && t.status !== status) return false;
      const hay = `${t.id} ${t.user_email ?? ''} ${t.subject ?? ''} ${t.message}`.toLowerCase();
      return !q || hay.includes(q.toLowerCase());
    });
  }, [items, q, status]);

  if (loading) return <Center py="xl"><Loader color="brand" /></Center>;

  return (
    <>
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>Обращения</Title>
          <Text c="dimmed" size="sm">
            Доступно владельцу и специалистам поддержки
          </Text>
        </div>
      </Group>

      <Group mb="md">
        <TextInput placeholder="Поиск по ID или email" value={q} onChange={(e) => setQ(e.currentTarget.value)} />
        <Select
          placeholder="Статус"
          data={['Все', 'new', 'answered', 'waiting_user', 'closed']}
          value={status}
          onChange={setStatus}
        />
      </Group>
      <Card withBorder padding={0} radius="md">
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>Пользователь</Table.Th>
              <Table.Th>Тема</Table.Th>
              <Table.Th>Статус</Table.Th>
              <Table.Th>Дата</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {filtered.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={6}>
                  <Text c="dimmed" ta="center" py="lg">
                    Обращений нет
                  </Text>
                </Table.Td>
              </Table.Tr>
            ) : (
              filtered.map((t) => (
                <Table.Tr key={t.id}>
                  <Table.Td>#{t.id}</Table.Td>
                  <Table.Td>{t.user_email ?? t.id}</Table.Td>
                  <Table.Td>{t.subject || t.message.slice(0, 40)}</Table.Td>
                  <Table.Td>
                    <Badge color="brand" variant="light">
                      {STATUS[t.status] ?? t.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{t.created_at ? new Date(t.created_at).toLocaleString('ru-RU') : '—'}</Table.Td>
                  <Table.Td>
                    <Button component={Link} to={`/support/tickets/${t.id}`} size="xs" variant="subtle">
                      Открыть
                    </Button>
                  </Table.Td>
                </Table.Tr>
              ))
            )}
          </Table.Tbody>
        </Table>
      </Card>
    </>
  );
}
