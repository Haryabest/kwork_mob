'use client';

import { Button, Paper, PasswordInput, Stack, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useRouter, useSearchParams } from 'next/navigation';
import { type FormEvent, Suspense, useState } from 'react';
import { AuthPage } from '../../../components/AuthPage';
import { api, apiMessage } from '../../../services/api';

function ResetPasswordForm() {
  const router = useRouter();
  const token = useSearchParams().get('token');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (password !== confirm) {
      return notifications.show({ color: 'red', message: 'Пароли не совпадают' });
    }
    setLoading(true);
    try {
      await api.post('/auth/password/confirm', {
        token,
        password,
        password_confirm: confirm,
      });
      notifications.show({ color: 'green', message: 'Пароль изменён' });
      router.replace('/');
    } catch (error) {
      notifications.show({ color: 'red', message: apiMessage(error) });
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthPage>
      <Paper withBorder shadow="md" radius="lg" p="xl" w="100%">
        <form onSubmit={submit}>
          <Stack>
            <div>
              <Title order={2}>Новый пароль</Title>
              <Text size="sm" c="dimmed">
                Придумайте надёжный пароль
              </Text>
            </div>
            <PasswordInput
              label="Новый пароль"
              minLength={8}
              required
              value={password}
              onChange={(e) => setPassword(e.currentTarget.value)}
            />
            <PasswordInput
              label="Повторите пароль"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.currentTarget.value)}
            />
            <Button type="submit" loading={loading} disabled={!token}>
              Сохранить пароль
            </Button>
          </Stack>
        </form>
      </Paper>
    </AuthPage>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordForm />
    </Suspense>
  );
}
