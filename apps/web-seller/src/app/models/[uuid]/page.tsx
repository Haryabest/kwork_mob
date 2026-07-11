import { Badge, Button, Card, Group, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { IconDownload, IconShare2, IconStar } from '@tabler/icons-react';
import Link from 'next/link';
import { SellerShell } from '../../../components/SellerShell';

export default async function ModelDetailPage({ params }: { params: Promise<{ uuid: string }> }) {
  const { uuid } = await params;
  return <SellerShell><Stack gap="lg"><Group justify="space-between"><div><Title order={2}>Модель</Title><Text c="dimmed" size="sm">{uuid}</Text></div><Badge color="gray">Не опубликована</Badge></Group>
    <SimpleGrid cols={{ base: 1, md: 2 }}><Card withBorder mih={280}><Text c="dimmed" ta="center" pt={110}>Предпросмотр 3D-модели</Text></Card><Card withBorder><Stack><Title order={3}>Действия</Title><Button leftSection={<IconDownload size={16} />} disabled>Скачать GLB (Ozon)</Button><Button variant="light" leftSection={<IconDownload size={16} />} disabled>Скачать USDZ (Wildberries)</Button><Button component={Link} href={`/viewer/${uuid}`} variant="light" leftSection={<IconShare2 size={16} />}>Открыть просмотрщик</Button><Button variant="subtle" leftSection={<IconStar size={16} />}>Оценить качество</Button></Stack></Card></SimpleGrid>
    <Card withBorder><Title order={3} mb="sm">Данные модели</Title><Text size="sm" c="dimmed">Детали появятся после загрузки данных из API.</Text></Card>
  </Stack></SellerShell>;
}
