'use client';

import { Button, Card, Center, Stack, Text, Title } from '@mantine/core';
import { IconUsers } from '@tabler/icons-react';
import { use } from 'react';
import { useRouter } from 'next/navigation';

export default function InvitePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const router = useRouter();
  return <Center mih="100vh" p="md" style={{ background: '#f5f6fa' }}><Card withBorder shadow="md" radius="lg" p="xl" maw={440}>
    <Stack align="center"><IconUsers size={44} color="#0B7A73" /><Title order={2} ta="center">Приглашение в команду</Title><Text c="dimmed" ta="center">Вас пригласили присоединиться к компании в KWork Mob.</Text><Text size="xs" c="dimmed">Код: {token.slice(0, 8)}</Text><Button fullWidth onClick={() => router.push(`/register?invite=${token}`)}>Принять приглашение</Button><Button fullWidth variant="subtle" onClick={() => router.push('/')}>У меня уже есть аккаунт</Button></Stack>
  </Card></Center>;
}
