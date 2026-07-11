import { Badge, Button, Card, Group, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { IconX } from '@tabler/icons-react';
import { SellerShell } from '../../../components/SellerShell';

export default async function OrderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <SellerShell><Stack gap="lg"><Group justify="space-between"><div><Title order={2}>Заказ #{id}</Title><Text size="sm" c="dimmed">Детали генерации</Text></div><Badge color="gray">Новый</Badge></Group>
    <SimpleGrid cols={{ base: 1, md: 3 }}>{[['Тариф', '—'], ['Стоимость', '— ₽'], ['Создан', '—']].map(([label, value]) => <Card key={label} withBorder><Text size="sm" c="dimmed">{label}</Text><Text fw={600} size="lg">{value}</Text></Card>)}</SimpleGrid>
    <Card withBorder><Title order={3} mb="sm">Этапы выполнения</Title><Text c="dimmed" size="sm">Статус будет обновляться автоматически.</Text></Card>
    <Button color="red" variant="light" leftSection={<IconX size={16} />} w="fit-content">Отменить заказ</Button>
  </Stack></SellerShell>;
}
