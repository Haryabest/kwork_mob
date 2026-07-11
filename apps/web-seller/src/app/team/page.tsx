'use client';

import { Button, Card, Group, Modal, NumberInput, Select, Stack, Table, Text, TextInput, Title } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconUserPlus } from '@tabler/icons-react';
import Link from 'next/link';
import { SellerShell } from '../../components/SellerShell';

export default function TeamPage() {
  const [opened, { open, close }] = useDisclosure(false);
  return (
    <SellerShell>
      <Title order={2} mb="xs">
        Команда
      </Title>
      <Text c="dimmed" size="sm" mb="lg">
        Только для Owner компании
      </Text>
      <Group mb="md"><Button leftSection={<IconUserPlus size={16} />} onClick={open}>Пригласить сотрудника</Button><Button component={Link} href="/team/roles" variant="subtle">Роли</Button><Button component={Link} href="/team/policies" variant="subtle">Политики</Button><Button component={Link} href="/team/audit" variant="subtle">Аудит</Button><Button component={Link} href="/team/sessions" variant="subtle">Сессии</Button><Button component={Link} href="/team/api-keys" variant="subtle">API-ключи</Button></Group>
      <Card withBorder padding="lg" radius="md">
        <Group grow mb="md"><TextInput label="Поиск" placeholder="Имя или email" /><Select label="Роль" placeholder="Все роли" data={['Owner', 'Manager', 'Photographer', 'Viewer']} /></Group>
        <Table miw={750}><Table.Thead><Table.Tr><Table.Th>Сотрудник</Table.Th><Table.Th>Роль</Table.Th><Table.Th>Статус</Table.Th><Table.Th>Активных заказов</Table.Th><Table.Th>Активность</Table.Th></Table.Tr></Table.Thead><Table.Tbody><Table.Tr><Table.Td colSpan={5}><Text c="dimmed" ta="center" py="xl">В команде пока нет сотрудников</Text></Table.Td></Table.Tr></Table.Tbody></Table>
      </Card>
      <Modal opened={opened} onClose={close} title="Пригласить сотрудника" centered><Stack><TextInput label="Email" type="email" required /><Select label="Роль" data={['Manager', 'Photographer', 'Viewer']} defaultValue="Photographer" /><NumberInput label="Лимит активных заказов" min={1} /><NumberInput label="Лимит расходов в месяц, ₽" min={0} /><Select label="Срок действия приглашения" data={['1 день', '7 дней', '30 дней']} defaultValue="7 дней" /><Button>Отправить приглашение</Button></Stack></Modal>
    </SellerShell>
  );
}
