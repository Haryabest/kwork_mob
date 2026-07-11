import { Button, Card, Checkbox, Group, Stack, Table, Text, TextInput, Textarea, Title, Loader, Center, Badge } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';
import { api, getApiError } from '../../services/api';

type Faq = {
  id: number;
  category: string;
  question: string;
  answer: string;
  version: number;
  is_published: boolean;
};

export default function FaqEditorPage() {
  const [items, setItems] = useState<Faq[]>([]);
  const [loading, setLoading] = useState(true);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState({ category: 'Общее', question: '', answer: '', is_published: true });
  const [saving, setSaving] = useState(false);

  async function load() {
    const { data } = await api.get<{ items: Faq[] }>('/faq/all');
    setItems(data.items ?? []);
  }

  useEffect(() => {
    load()
      .catch((e) => notifications.show({ color: 'red', message: getApiError(e) }))
      .finally(() => setLoading(false));
  }, []);

  async function save() {
    if (form.question.length < 3 || form.answer.length < 3) {
      return notifications.show({ color: 'red', message: 'Вопрос и ответ обязательны' });
    }
    setSaving(true);
    try {
      if (editId) await api.patch(`/faq/${editId}`, form);
      else await api.post('/faq', form);
      setForm({ category: 'Общее', question: '', answer: '', is_published: true });
      setEditId(null);
      await load();
      notifications.show({ color: 'green', message: editId ? 'Обновлено' : 'Создано' });
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <Center py="xl"><Loader color="brand" /></Center>;

  return (
    <>
      <Title order={2} mb="xs">
        FAQ
      </Title>
      <Text c="dimmed" size="sm" mb="lg">
        Редактирование вопросов/ответов с версионированием
      </Text>
      <Card withBorder radius="md" padding="lg" mb="lg">
        <Stack>
          <TextInput
            label="Категория"
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.currentTarget.value })}
          />
          <TextInput
            label="Вопрос"
            value={form.question}
            onChange={(e) => setForm({ ...form, question: e.currentTarget.value })}
          />
          <Textarea
            label="Ответ"
            minRows={4}
            value={form.answer}
            onChange={(e) => setForm({ ...form, answer: e.currentTarget.value })}
          />
          <Checkbox
            label="Опубликован"
            checked={form.is_published}
            onChange={(e) => setForm({ ...form, is_published: e.currentTarget.checked })}
          />
          <Group>
            <Button loading={saving} onClick={save}>
              {editId ? 'Сохранить версию' : 'Опубликовать'}
            </Button>
            {editId && (
              <Button
                variant="subtle"
                onClick={() => {
                  setEditId(null);
                  setForm({ category: 'Общее', question: '', answer: '', is_published: true });
                }}
              >
                Отмена
              </Button>
            )}
          </Group>
        </Stack>
      </Card>

      <Card withBorder padding={0}>
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Категория</Table.Th>
              <Table.Th>Вопрос</Table.Th>
              <Table.Th>Версия</Table.Th>
              <Table.Th>Статус</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {items.map((item) => (
              <Table.Tr key={item.id}>
                <Table.Td>{item.category}</Table.Td>
                <Table.Td>{item.question}</Table.Td>
                <Table.Td>v{item.version}</Table.Td>
                <Table.Td>
                  <Badge color={item.is_published ? 'teal' : 'gray'} variant="light">
                    {item.is_published ? 'Опубликован' : 'Черновик'}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Button
                    size="xs"
                    variant="subtle"
                    onClick={() => {
                      setEditId(item.id);
                      setForm({
                        category: item.category,
                        question: item.question,
                        answer: item.answer,
                        is_published: item.is_published,
                      });
                    }}
                  >
                    Править
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>
    </>
  );
}
