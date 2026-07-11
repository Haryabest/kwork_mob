'use client';

import { Button, Paper, PinInput, Stack, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useState } from 'react';
import { AuthPage } from '../../../components/AuthPage';
import { auth } from '../../../lib/auth';
import { api, apiMessage } from '../../../services/api';

function VerifyForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const email = params.get('email') ?? '';

  async function submit() {
    setLoading(true);
    try {
      const { data } = await api.post<{
        status: string;
        access_token?: string;
        refresh_token?: string;
      }>('/auth/verify-email', { email, code });
      if (data.access_token && data.refresh_token) {
        auth.setTokens(data.access_token, data.refresh_token);
      }
      router.push('/register/type');
    } catch (error) {
      notifications.show({ color: 'red', message: apiMessage(error, 'Неверный код') });
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthPage>
      <Paper withBorder shadow="md" radius="lg" p="xl" w="100%">
        <Stack>
          <div>
            <Title order={2}>Подтвердите email</Title>
            <Text size="sm" c="dimmed">
              Код отправлен на {email || 'вашу почту'}
            </Text>
          </div>
          <PinInput length={6} oneTimeCode value={code} onChange={setCode} />
          <Button disabled={code.length !== 6} loading={loading} onClick={submit}>
            Подтвердить
          </Button>
        </Stack>
      </Paper>
    </AuthPage>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={null}>
      <VerifyForm />
    </Suspense>
  );
}
