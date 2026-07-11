import { Badge, Card, Center, Group, Stack, Text, Title } from '@mantine/core';
import { IconBox } from '@tabler/icons-react';

export default async function ViewerPage({
  params,
}: {
  params: Promise<{ uuid: string }>;
}) {
  const { uuid } = await params;
  return (
    <Center mih="100vh" p="md" style={{ background: '#f5f6fa' }}><Stack maw={960} w="100%"><Group justify="space-between"><div><Title order={2}>KWork Mob Viewer</Title><Text c="dimmed" size="sm">Модель {uuid}</Text></div><Badge color="brand">Публичный просмотр</Badge></Group>
      <Card withBorder mih={520} style={{ background: 'linear-gradient(135deg, #d0efed, #f4f7f7)' }}><Center h="100%"><Stack align="center"><IconBox size={70} stroke={1} color="#0B7A73" /><Text fw={600}>3D-просмотрщик</Text><Text c="dimmed" size="sm">Интерактивная модель появится после обработки</Text></Stack></Center></Card>
      <Text size="xs" c="dimmed" ta="center">KWork Mob · защищённая публичная ссылка</Text></Stack></Center>
  );
}
