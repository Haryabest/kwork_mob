'use client';

import { Button, Card, Group, Modal, Stack, Table, Text, TextInput, Title } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { SellerShell } from '../../../components/SellerShell';

export default function ApiKeysPage() {
  const [opened, { open, close }] = useDisclosure(false);
  return <SellerShell><Group justify="space-between" mb="lg"><div><Title order={2}>API-ключи</Title><Text c="dimmed" size="sm">Интеграции компании</Text></div><Button onClick={open}>Создать ключ</Button></Group>
    <Card withBorder><Table><Table.Thead><Table.Tr><Table.Th>Название</Table.Th><Table.Th>Ключ</Table.Th><Table.Th>Создан</Table.Th><Table.Th /></Table.Tr></Table.Thead><Table.Tbody><Table.Tr><Table.Td colSpan={4}><Text ta="center" c="dimmed" py="xl">API-ключей пока нет</Text></Table.Td></Table.Tr></Table.Tbody></Table></Card>
    <Modal opened={opened} onClose={close} title="Создать API-ключ"><Stack><TextInput label="Название ключа" placeholder="Интеграция склада" /><Button>Создать</Button></Stack></Modal>
  </SellerShell>;
}
