'use client';

import { ActionIcon, Badge, Button, Card, Group, SimpleGrid, Stack, Table, Text, ThemeIcon, Title } from '@mantine/core';
import { IconArrowUpRight, IconBox, IconCash, IconPlus, IconUsers } from '@tabler/icons-react';
import Link from 'next/link';
import { SellerShell } from '../../components/SellerShell';

const stats = [
  ['Баланс', '0 ₽', IconCash], ['Генераций за месяц', '0', IconBox],
  ['Активных заказов', '0', IconArrowUpRight], ['Сотрудников', '0', IconUsers],
] as const;

export default function DashboardPage() {
  return <SellerShell><Stack gap="lg">
    <Group justify="space-between"><div><Title order={2}>Добро пожаловать</Title><Text c="dimmed" size="sm">Обзор вашего кабинета</Text></div><Button component={Link} href="/balance" leftSection={<IconPlus size={16} />}>Пополнить баланс</Button></Group>
    <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>{stats.map(([label, value, Icon]) => <Card key={label} withBorder><Group justify="space-between"><div><Text size="sm" c="dimmed">{label}</Text><Text fw={700} size="xl">{value}</Text></div><ThemeIcon variant="light" color="brand" size="lg"><Icon size={20} /></ThemeIcon></Group></Card>)}</SimpleGrid>
    <SimpleGrid cols={{ base: 1, lg: 2 }}><Card withBorder><Group justify="space-between" mb="md"><div><Title order={3}>Последние модели</Title><Text size="sm" c="dimmed">5 последних генераций</Text></div><Button component={Link} href="/models" variant="subtle">Все модели</Button></Group>
      <Table verticalSpacing="sm"><Table.Thead><Table.Tr><Table.Th>Название</Table.Th><Table.Th>Статус</Table.Th><Table.Th /></Table.Tr></Table.Thead><Table.Tbody><Table.Tr><Table.Td colSpan={3}><Text c="dimmed" ta="center" py="md">Моделей пока нет</Text></Table.Td></Table.Tr></Table.Tbody></Table>
    </Card><Card withBorder><Title order={3} mb="md">Быстрые действия</Title><Stack><Button component={Link} href="/models" variant="light" leftSection={<IconBox size={16} />}>Мои модели</Button><Button component={Link} href="/balance" variant="light" leftSection={<IconCash size={16} />}>Пополнить баланс</Button><Button component={Link} href="/team" variant="light" leftSection={<IconUsers size={16} />}>Пригласить сотрудника</Button></Stack></Card></SimpleGrid>
  </Stack></SellerShell>;
}
