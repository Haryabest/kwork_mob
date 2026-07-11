'use client';

import { Badge, Card, Group, Select, Table, Text, TextInput, Title } from '@mantine/core';
import { IconSearch } from '@tabler/icons-react';
import { SellerShell } from '../../components/SellerShell';

export default function ModelsPage() {
  return (
    <SellerShell>
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>Мои модели</Title>
          <Text c="dimmed" size="sm">
            История генераций
          </Text>
        </div>
        <Badge variant="light">0 моделей</Badge>
      </Group>
      <Card withBorder>
        <Group mb="md" grow align="end">
          <TextInput label="Поиск" placeholder="Название модели" leftSection={<IconSearch size={16} />} />
          <Select label="Статус" placeholder="Все статусы" data={['В процессе', 'Готово', 'Ошибка', 'Отменено']} clearable />
          <Select label="Категория" placeholder="Все категории" data={['Одежда', 'Обувь', 'Аксессуары']} clearable />
          <Select label="Тариф" placeholder="Все тарифы" data={['Малый', 'Крупный']} clearable />
        </Group>
        <Table highlightOnHover verticalSpacing="sm" miw={720}>
          <Table.Thead><Table.Tr><Table.Th>Модель</Table.Th><Table.Th>Дата</Table.Th><Table.Th>Категория</Table.Th><Table.Th>Тариф</Table.Th><Table.Th>Публикация</Table.Th><Table.Th /></Table.Tr></Table.Thead>
          <Table.Tbody><Table.Tr><Table.Td colSpan={6}><Text c="dimmed" ta="center" py="xl">Моделей пока нет. Создайте первую в мобильном приложении.</Text></Table.Td></Table.Tr></Table.Tbody>
        </Table>
      </Card>
    </SellerShell>
  );
}
