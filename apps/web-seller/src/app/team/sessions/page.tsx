'use client';

import { Button, Card, Table, Text, Title } from '@mantine/core';
import { SellerShell } from '../../../components/SellerShell';

export default function TeamSessionsPage() {
  return <SellerShell><Title order={2}>Сессии сотрудников</Title><Text c="dimmed" size="sm" mb="lg">Активные авторизации команды</Text><Card withBorder>
    <Table><Table.Thead><Table.Tr><Table.Th>Сотрудник</Table.Th><Table.Th>Устройство</Table.Th><Table.Th>IP</Table.Th><Table.Th>Последняя активность</Table.Th><Table.Th /></Table.Tr></Table.Thead><Table.Tbody><Table.Tr><Table.Td colSpan={5}><Text c="dimmed" ta="center" py="xl">Активных сессий нет</Text></Table.Td></Table.Tr></Table.Tbody></Table>
    <Button color="red" variant="light" mt="md">Завершить все сессии</Button>
  </Card></SellerShell>;
}
