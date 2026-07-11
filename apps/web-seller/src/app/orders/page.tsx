'use client';

import { Card, Group, Select, Table, Text, TextInput, Title } from '@mantine/core';
import { IconSearch } from '@tabler/icons-react';
import { SellerShell } from '../../components/SellerShell';

export default function OrdersPage() {
  return (
    <SellerShell>
      <Title order={2} mb="xs">
        Заказы
      </Title>
      <Text c="dimmed" size="sm" mb="lg">
        Статусы генераций
      </Text>
      <Card withBorder padding="lg" radius="md">
        <Group mb="md" grow><TextInput label="Поиск" placeholder="Номер заказа" leftSection={<IconSearch size={16} />} /><Select label="Статус" placeholder="Все статусы" data={['Новый', 'В обработке', 'Готов', 'Отменён']} clearable /></Group>
        <Table highlightOnHover miw={680}><Table.Thead><Table.Tr><Table.Th>Заказ</Table.Th><Table.Th>Создан</Table.Th><Table.Th>Тариф</Table.Th><Table.Th>Стоимость</Table.Th><Table.Th>Статус</Table.Th></Table.Tr></Table.Thead><Table.Tbody>
          <Table.Tr><Table.Td colSpan={5}><Text c="dimmed" ta="center" py="xl">Заказов пока нет</Text></Table.Td></Table.Tr>
        </Table.Tbody></Table>
      </Card>
    </SellerShell>
  );
}
