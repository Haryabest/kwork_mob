'use client';

import {
  Anchor,
  Button,
  Checkbox,
  Divider,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
  Group,
} from '@mantine/core';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { FormEvent, useState } from 'react';
import { notifications } from '@mantine/notifications';
import { auth } from '../lib/auth';
import { api, apiMessage } from '../services/api';

/** §20.1 — поп-ап авторизации */
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
      const { data } = await api.post<{ access_token: string; refresh_token: string }>('/auth/login', {
        email,
        password,
        remember,
      });
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
    <div className="vz-auth-card">
      <Stack gap="lg">
        <Group gap="sm">
          <div className="vz-logo-mark">3D</div>
          <div>
            <Text fw={700} size="sm" lh={1.2}>
              3dvektor
            </Text>
            <Text size="xs" c="#6d6c77">
              3D для селлеров WB / Ozon
            </Text>
          </div>
        </Group>

        <div>
          <Title order={2} style={{ letterSpacing: '-0.03em' }}>
            Авторизация
          </Title>
          <Text c="#6d6c77" size="sm" mt={6}>
            Войдите в личный кабинет
          </Text>
        </div>

        <form onSubmit={onSubmit}>
          <Stack gap="md">
            <TextInput
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.currentTarget.value)}
              required
              autoComplete="username"
              placeholder="seller@example.com"
              size="md"
            />
            <PasswordInput
              label="Пароль"
              value={password}
              onChange={(e) => setPassword(e.currentTarget.value)}
              required
              autoComplete="current-password"
              size="md"
              visibilityToggleButtonProps={{ 'aria-label': 'Показать пароль' }}
            />
            <Checkbox
              checked={remember}
              onChange={(e) => setRemember(e.currentTarget.checked)}
              label="Запомнить меня"
            />
            <Button type="submit" fullWidth loading={loading} size="md">
              Войти
            </Button>
          </Stack>
        </form>

        <Divider color="rgba(0,87,184,0.1)" />

        <Stack gap={8} align="center">
          <Anchor component={Link} href="/password/forgot" size="sm" c="#6d6c77">
            Забыли пароль?
          </Anchor>
          <Text size="sm" ta="center">
            Ещё нет аккаунта?{' '}
            <Anchor component={Link} href="/register" fw={700} c="brand">
              Зарегистрироваться
            </Anchor>
          </Text>
        </Stack>
      </Stack>
    </div>
  );
}
