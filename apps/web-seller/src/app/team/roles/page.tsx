'use client';

import { Button, Card, Checkbox, Group, Modal, Stack, Table, Text, TextInput, Title } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { SellerShell } from '../../../components/SellerShell';

const permissions = ['Создание заказов', 'Скачивание моделей', 'Добавление ссылок', 'Приглашение сотрудников', 'Управление ролями', 'Просмотр финансов'];
export default function RolesPage() {
  const [opened, { open, close }] = useDisclosure(false);
  return <SellerShell><Group justify="space-between" mb="lg"><div><Title order={2}>Роли</Title><Text c="dimmed" size="sm">Права доступа сотрудников</Text></div><Button onClick={open}>Создать роль</Button></Group>
    <Card withBorder><Table><Table.Thead><Table.Tr><Table.Th>Роль</Table.Th><Table.Th>Сотрудников</Table.Th><Table.Th>Права</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{['Owner', 'Manager', 'Photographer', 'Viewer'].map((role) => <Table.Tr key={role}><Table.Td fw={600}>{role}</Table.Td><Table.Td>0</Table.Td><Table.Td><Text size="sm" c="dimmed">Предопределённая роль</Text></Table.Td></Table.Tr>)}</Table.Tbody></Table></Card>
    <Modal opened={opened} onClose={close} title="Новая роль"><Stack><TextInput label="Название роли" required />{permissions.map((permission) => <Checkbox key={permission} label={permission} />)}<Button>Сохранить роль</Button></Stack></Modal>
  </SellerShell>;
}
