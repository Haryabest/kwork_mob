'use client';

import {
  Anchor,
  Button,
  Checkbox,
  Paper,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, type FormEvent, useState } from 'react';
import { AuthPage } from '../../components/AuthPage';
import { api, apiMessage } from '../../services/api';

const CONSENT_SLUGS = ['terms', 'privacy', 'offer', 'rights', 'nsfw_rules'] as const;

function RegisterForm() {
  const router = useRouter();
  const invite = useSearchParams().get('invite');
  const [form, setForm] = useState({ email: '', password: '', passwordConfirm: '' });
  const [consents, setConsents] = useState<Record<string, boolean>>({
    terms: false,
    privacy: false,
    offer: false,
    rights: false,
    nsfw_rules: false,
  });
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (form.password !== form.passwordConfirm) {
      return notifications.show({ color: 'red', message: 'Пароли не совпадают' });
    }
    if (!CONSENT_SLUGS.every((s) => consents[s])) {
      return notifications.show({ color: 'red', message: 'Примите все обязательные согласия' });
    }
    setLoading(true);
    try {
      const { data } = await api.post<{ email: string; dev_code?: string }>('/auth/register', {
        email: form.email,
        password: form.password,
        password_confirm: form.passwordConfirm,
        consents: CONSENT_SLUGS.filter((s) => consents[s]),
      });
      if (data.dev_code) {
        notifications.show({ color: 'blue', message: `Dev-код: ${data.dev_code}`, autoClose: 15000 });
      }
      const q = new URLSearchParams({ email: form.email });
      if (invite) q.set('invite', invite);
      router.push(`/register/verify?${q.toString()}`);
    } catch (error) {
      notifications.show({ color: 'red', message: apiMessage(error) });
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthPage>
      <Paper withBorder shadow="md" radius="lg" p="xl" w="100%" maw={520}>
        <form onSubmit={submit}>
          <Stack>
            <div>
              <Title order={2}>Регистрация</Title>
              <Text size="sm" c="dimmed">
                Только email и пароль · ФИО не обязательно
              </Text>
            </div>
            <TextInput
              label="Email"
              type="email"
              required
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.currentTarget.value })}
            />
            <PasswordInput
              label="Пароль"
              description="Минимум 8 символов, буквы и цифры"
              required
              minLength={8}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.currentTarget.value })}
            />
            <PasswordInput
              label="Подтверждение пароля"
              required
              value={form.passwordConfirm}
              onChange={(e) => setForm({ ...form, passwordConfirm: e.currentTarget.value })}
            />

            <Stack gap="xs">
              <Checkbox
                checked={consents.terms}
                onChange={(e) => setConsents({ ...consents, terms: e.currentTarget.checked })}
                label={
                  <>
                    Принимаю{' '}
                    <Anchor component={Link} href="/legal/terms" target="_blank">
                      пользовательское соглашение
                    </Anchor>
                  </>
                }
              />
              <Checkbox
                checked={consents.privacy}
                onChange={(e) => setConsents({ ...consents, privacy: e.currentTarget.checked })}
                label={
                  <>
                    Согласие на{' '}
                    <Anchor component={Link} href="/legal/privacy" target="_blank">
                      обработку персональных данных
                    </Anchor>
                  </>
                }
              />
              <Checkbox
                checked={consents.offer}
                onChange={(e) => setConsents({ ...consents, offer: e.currentTarget.checked })}
                label={
                  <>
                    Принимаю{' '}
                    <Anchor component={Link} href="/legal/offer" target="_blank">
                      оферту
                    </Anchor>
                  </>
                }
              />
              <Checkbox
                checked={consents.rights}
                onChange={(e) => setConsents({ ...consents, rights: e.currentTarget.checked })}
                label={
                  <>
                    Подтверждаю{' '}
                    <Anchor component={Link} href="/legal/rights" target="_blank">
                      права на товары
                    </Anchor>
                  </>
                }
              />
              <Checkbox
                checked={consents.nsfw_rules}
                onChange={(e) => setConsents({ ...consents, nsfw_rules: e.currentTarget.checked })}
                label={
                  <>
                    Ознакомлен с{' '}
                    <Anchor component={Link} href="/legal/nsfw_rules" target="_blank">
                      правилами запрещённого контента / возвратов
                    </Anchor>
                  </>
                }
              />
            </Stack>

            <Button type="submit" loading={loading}>
              Зарегистрироваться
            </Button>
            <Text ta="center" size="sm">
              Уже есть аккаунт?{' '}
              <Anchor component={Link} href="/">
                Войти
              </Anchor>
            </Text>
          </Stack>
        </form>
      </Paper>
    </AuthPage>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={null}>
      <RegisterForm />
    </Suspense>
  );
}
