'use client';

import { Center, Loader, Stack, Text, Title } from '@mantine/core';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { AuthCard } from '../components/AuthCard';
import { auth } from '../lib/auth';
import { api } from '../services/api';

/** Стартовая страница с поп-ап авторизации (§20.1) */
export default function HomePage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!auth.getAccessToken()) {
      setReady(true);
      return;
    }
    api
      .get<{ status?: string }>('/user/me')
      .then(({ data }) => {
        router.replace(data.status === 'pending_type' ? '/register/type' : '/dashboard');
      })
      .catch(() => {
        auth.clear();
        setReady(true);
      });
  }, [router]);

  if (!ready) {
    return (
      <Center mih="100vh">
        <Loader color="brand" />
      </Center>
    );
  }

  return (
    <Center
      mih="100vh"
      p="md"
      style={{
        background:
          'radial-gradient(circle at 15% 20%, rgba(11,122,115,0.14), transparent 42%), radial-gradient(circle at 85% 75%, rgba(15,76,92,0.12), transparent 40%), #f4f7f7',
      }}
    >
      <Stack align="center" gap="lg">
        <div style={{ textAlign: 'center' }}>
          <Title order={1} c="brand">
            KWork Mob
          </Title>
          <Text c="dimmed">3D-модели для маркетплейсов</Text>
        </div>
        <AuthCard />
      </Stack>
    </Center>
  );
}
