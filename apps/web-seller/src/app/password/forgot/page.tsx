'use client';

import { Anchor, Button, Paper, Stack, Text, TextInput, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import Link from 'next/link';
import { type FormEvent, useState } from 'react';
import { AuthPage } from '../../../components/AuthPage';
import { api, apiMessage } from '../../../services/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [devToken, setDevToken] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post<{ message: string; dev_token?: string }>('/auth/password/forgot', {
        email,
      });
      setSent(true);
      if (data.dev_token) setDevToken(data.dev_token);
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
              <Title order={2}>Восстановление пароля</Title>
              <Text size="sm" c="dimmed">
                {sent ? 'Проверьте входящие письма' : 'Мы отправим ссылку на вашу почту'}
              </Text>
            </div>
            {!sent && (
              <>
                <TextInput
                  label="Email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.currentTarget.value)}
                />
                <Button type="submit" loading={loading}>
                  Отправить ссылку
                </Button>
              </>
            )}
            {devToken && (
              <Anchor component={Link} href={`/password/reset?token=${encodeURIComponent(devToken)}`}>
                Dev: открыть сброс пароля
              </Anchor>
            )}
            <Anchor component={Link} href="/" size="sm">
              Вернуться ко входу
            </Anchor>
          </Stack>
        </form>
      </Paper>
    </AuthPage>
  );
}
