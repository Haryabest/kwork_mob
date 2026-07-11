'use client';

import {
  Anchor,
  Button,
  Checkbox,
  Divider,
  Paper,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { FormEvent, useState } from 'react';
import { notifications } from '@mantine/notifications';
import { auth } from '../lib/auth';
import { api, apiMessage } from '../services/api';

export function AuthCard() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post<{ access_token: string; refresh_token: string }>('/auth/login', { email, password, remember });
      auth.setTokens(data.access_token, data.refresh_token);
      const me = await api.get<{ status?: string }>('/user/me');
      router.replace(me.data.status === 'pending_type' ? '/register/type' : '/dashboard');
    } catch (error) {
      notifications.show({ color: 'red', message: apiMessage(error, 'Неверный email или пароль') });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Paper shadow="md" radius="lg" p="xl" w={420} maw="100%" withBorder>
      <Stack gap="md">
        <div>
          <Title order={2}>Авторизация</Title>
          <Text c="dimmed" size="sm">
            Личный кабинет селлера
          </Text>
        </div>

        <form onSubmit={onSubmit}>
          <Stack gap="sm">
            <TextInput
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.currentTarget.value)}
              required
              autoComplete="username"
              placeholder="seller@example.com"
            />
            <PasswordInput
              label="Пароль"
              value={password}
              onChange={(e) => setPassword(e.currentTarget.value)}
              required
              autoComplete="current-password"
            />
            <Checkbox checked={remember} onChange={(e) => setRemember(e.currentTarget.checked)} label="Запомнить меня" />
            <Button type="submit" fullWidth loading={loading} mt="xs">
              Войти
            </Button>
          </Stack>
        </form>

        <Divider />

        <Stack gap={4} align="center">
          <Anchor component={Link} href="/password/forgot" size="sm" c="dimmed">
            Забыли пароль?
          </Anchor>
          <Text size="sm">
            Ещё нет аккаунта?{' '}
            <Anchor component={Link} href="/register" fw={600} c="brand">
              Зарегистрироваться
            </Anchor>
          </Text>
        </Stack>
      </Stack>
    </Paper>
  );
}
