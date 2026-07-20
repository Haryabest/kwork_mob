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
import { api, apiMessage } from '../services/api';
import { getRecaptchaToken, loginErrorDetail, recaptchaEnabled } from '../lib/recaptcha';
import { OAuthButtons } from './OAuthButtons';

/** §20.1 — авторизация + 2FA challenge + reCAPTCHA v3 */
export function AuthCard() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [loading, setLoading] = useState(false);
  const [challenge, setChallenge] = useState<string | null>(null);
  const [code, setCode] = useState('');
  const [requiresCaptcha, setRequiresCaptcha] = useState(false);

  async function finishLogin() {
    const me = await api.get<{ status?: string }>('/user/me');
    router.replace(me.data.status === 'pending_type' ? '/register/type' : '/dashboard');
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      if (challenge) {
        await api.post('/auth/2fa/verify-login', {
          challenge_token: challenge,
          code: code.trim(),
        });
        await finishLogin();
        return;
      }
      const payload: Record<string, unknown> = {
        email,
        password,
        remember_me: remember,
      };
      if (requiresCaptcha || recaptchaEnabled()) {
        const captcha = await getRecaptchaToken('login');
        if (captcha) payload.captcha_token = captcha;
      }
      const { data } = await api.post<{
        requires_2fa?: boolean;
        challenge_token?: string;
      }>('/auth/login', payload);
      if (data.requires_2fa && data.challenge_token) {
        setChallenge(data.challenge_token);
        notifications.show({ color: 'blue', message: 'Введите код из Authenticator' });
        return;
      }
      await finishLogin();
    } catch (error) {
      const detail = loginErrorDetail(error);
      if (detail.requires_captcha) setRequiresCaptcha(true);
      notifications.show({
        color: 'red',
        message: detail.message || apiMessage(error, 'Неверный email или пароль'),
      });
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
            {challenge ? 'Код 2FA' : 'Авторизация'}
          </Title>
          <Text c="#6d6c77" size="sm" mt={6}>
            {challenge ? 'Введите код из приложения-аутентификатора' : 'Войдите в личный кабинет'}
          </Text>
        </div>

        <form onSubmit={onSubmit}>
          <Stack gap="md">
            {!challenge ? (
              <>
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
                {requiresCaptcha && (
                  <Text size="xs" c="dimmed">
                    После нескольких неудачных попыток включена проверка reCAPTCHA
                  </Text>
                )}
              </>
            ) : (
              <TextInput
                label="Код 2FA"
                value={code}
                onChange={(e) => setCode(e.currentTarget.value)}
                required
                maxLength={8}
                size="md"
              />
            )}
            <Button type="submit" fullWidth loading={loading} size="md">
              {challenge ? 'Подтвердить' : 'Войти'}
            </Button>
            {challenge && (
              <Button
                variant="subtle"
                onClick={() => {
                  setChallenge(null);
                  setCode('');
                }}
              >
                Назад
              </Button>
            )}
          </Stack>
        </form>

        {!challenge && <OAuthButtons mode="login" disabled={loading} />}

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
