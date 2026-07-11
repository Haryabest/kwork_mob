'use client';

import { Card, Group, Select, Table, Text, Title } from '@mantine/core';
import { SellerShell } from '../../../components/SellerShell';

export default function AuditPage() {
  return <SellerShell><Title order={2}>Журнал аудита</Title><Text c="dimmed" size="sm" mb="lg">Действия сотрудников в компании</Text><Card withBorder>
    <Group grow mb="md"><Select label="Сотрудник" placeholder="Все сотрудники" data={[]} /><Select label="Событие" placeholder="Все события" data={['Вход', 'Создание заказа', 'Изменение роли']} /></Group>
    <Table><Table.Thead><Table.Tr><Table.Th>Дата</Table.Th><Table.Th>Сотрудник</Table.Th><Table.Th>Действие</Table.Th><Table.Th>IP-адрес</Table.Th></Table.Tr></Table.Thead><Table.Tbody><Table.Tr><Table.Td colSpan={4}><Text ta="center" c="dimmed" py="xl">Событий пока нет</Text></Table.Td></Table.Tr></Table.Tbody></Table>
  </Card></SellerShell>;
}
