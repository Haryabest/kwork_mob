'use client';

import { Button, Center, Stack, Text, Title, Loader } from '@mantine/core';
import { IconUsers } from '@tabler/icons-react';
import { use, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { notifications } from '@mantine/notifications';
import { api, apiMessage, API_URL } from '../../../services/api';
import { auth } from '../../../lib/auth';
import axios from 'axios';

export default function InvitePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const router = useRouter();
  const [info, setInfo] = useState<{ email: string; role: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    axios
      .get<{ email: string; role: string }>(`${API_URL}/company/invite/${token}`)
      .then(({ data }) => setInfo(data))
      .catch((e) => notifications.show({ color: 'red', message: apiMessage(e, 'Приглашение недействительно') }))
      .finally(() => setLoading(false));
  }, [token]);

  async function accept() {
    if (!auth.getAccessToken()) {
      router.push(`/register?invite=${token}`);
      return;
    }
    setBusy(true);
    try {
      await api.post(`/company/invite/${token}/accept`);
      notifications.show({ color: 'teal', message: 'Вы вступили в команду' });
      router.push('/dashboard');
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <Center mih="100vh" className="vz-canvas">
        <Loader color="brand" />
      </Center>
    );
  }

  return (
    <Center mih="100vh" p="md" className="vz-canvas">
      <div className="vz-auth-card">
        <Stack align="center" gap="md">
          <IconUsers size={44} color="#0057b8" />
          <Title order={2} ta="center">
            Приглашение в команду
          </Title>
          <Text c="#6d6c77" ta="center">
            {info
              ? `Роль «${info.role}» для ${info.email}`
              : 'Приглашение не найдено или истекло'}
          </Text>
          {info && (
            <>
              <Button fullWidth loading={busy} onClick={() => void accept()}>
                {auth.getAccessToken() ? 'Принять приглашение' : 'Зарегистрироваться и принять'}
              </Button>
              <Button fullWidth variant="subtle" onClick={() => router.push(`/?invite=${token}`)}>
                У меня уже есть аккаунт
              </Button>
            </>
          )}
        </Stack>
      </div>
    </Center>
  );
}
