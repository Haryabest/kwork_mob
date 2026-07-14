'use client';

import {
  Badge,
  Button,
  Checkbox,
  Code,
  Image,
  PasswordInput,
  Stack,
  Switch,
  Tabs,
  Text,
  TextInput,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useCallback, useEffect, useState } from 'react';
import { SellerShell } from '../../components/SellerShell';
import { PageHeader, Surface } from '../../components/ui';
import { api, apiMessage } from '../../services/api';

type Me = {
  id: number;
  email: string;
  full_name?: string | null;
  phone?: string | null;
  marketing_opt_in?: boolean;
  totp_enabled?: boolean;
  notification_prefs?: Record<string, boolean>;
};

type TwoFaStatus = {
  totp_enabled: boolean;
  is_company_owner?: boolean;
  owner_2fa_required?: boolean;
};

const PREF_LABELS: Record<string, string> = {
  push_enabled: 'Push-уведомления',
  email_enabled: 'Email-уведомления',
  generation_done: 'Генерация готова',
  refund: 'Возврат средств',
  source_expire: 'Истечение исходников',
  cleanup: 'Очистка хранилища',
  publish_reminder: 'Напоминание опубликовать',
  email_orders: 'Email о заказах',
  email_balance: 'Email о балансе',
};

/** §20.8 Профиль и настройки — 2FA + push prefs */
export default function SettingsPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [oldPass, setOldPass] = useState('');
  const [newPass, setNewPass] = useState('');
  const [prefs, setPrefs] = useState<Record<string, boolean>>({});
  const [marketing, setMarketing] = useState(true);
  const [twoFa, setTwoFa] = useState<TwoFaStatus | null>(null);
  const [setup, setSetup] = useState<{ secret?: string; qr_data_url?: string; challenge_token?: string } | null>(
    null,
  );
  const [totpCode, setTotpCode] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [m, s] = await Promise.all([
      api.get<Me>('/user/me'),
      api.get<TwoFaStatus>('/auth/2fa/status'),
    ]);
    setMe(m.data);
    setFullName(m.data.full_name || '');
    setPhone(m.data.phone || '');
    setMarketing(m.data.marketing_opt_in !== false);
    setPrefs({
      push_enabled: true,
      email_enabled: true,
      generation_done: true,
      refund: true,
      source_expire: true,
      cleanup: false,
      publish_reminder: true,
      email_orders: true,
      email_balance: true,
      ...(m.data.notification_prefs || {}),
    });
    setTwoFa(s.data);
  }, []);

  useEffect(() => {
    load().catch((e) => notifications.show({ color: 'red', message: apiMessage(e) }));
  }, [load]);

  async function saveProfile() {
    setBusy(true);
    try {
      await api.patch('/user/me', { full_name: fullName, phone });
      notifications.show({ color: 'teal', message: 'Профиль сохранён' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function changePassword() {
    setBusy(true);
    try {
      await api.post('/auth/password/change', { old_password: oldPass, new_password: newPass });
      setOldPass('');
      setNewPass('');
      notifications.show({ color: 'teal', message: 'Пароль обновлён' });
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function savePrefs() {
    setBusy(true);
    try {
      await api.patch('/user/me', {
        marketing_opt_in: marketing,
        notification_prefs: prefs,
      });
      notifications.show({ color: 'teal', message: 'Уведомления сохранены' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function start2fa() {
    setBusy(true);
    try {
      const { data } = await api.post<{ secret: string; qr_data_url?: string; challenge_token?: string }>(
        '/auth/2fa/setup',
      );
      setSetup(data);
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function confirm2fa() {
    setBusy(true);
    try {
      await api.post('/auth/2fa/confirm', {
        code: totpCode.trim(),
        challenge_token: setup?.challenge_token,
      });
      setSetup(null);
      setTotpCode('');
      notifications.show({ color: 'teal', message: '2FA включена' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function deleteAccount() {
    if (!confirm('Удалить аккаунт? Заявка на забвение (SLA 30 дней).')) return;
    try {
      await api.post('/user/me/delete-request');
      notifications.show({ color: 'orange', message: 'Заявка на удаление создана' });
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }

  return (
    <SellerShell>
      <PageHeader title="Профиль и настройки" description="Личные данные, 2FA и уведомления (§20.8 / §3.4.3)" />

      <Tabs defaultValue="profile">
        <Tabs.List mb="lg">
          <Tabs.Tab value="profile">Профиль</Tabs.Tab>
          <Tabs.Tab value="security">Безопасность</Tabs.Tab>
          <Tabs.Tab value="notifications">Уведомления</Tabs.Tab>
          <Tabs.Tab value="danger" color="red">
            Опасная зона
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="profile">
          <Surface style={{ maxWidth: 560 }}>
            <Stack gap="md">
              <TextInput label="Email" value={me?.email || ''} disabled size="md" />
              <TextInput label="ФИО" value={fullName} onChange={(e) => setFullName(e.currentTarget.value)} size="md" />
              <TextInput label="Телефон" value={phone} onChange={(e) => setPhone(e.currentTarget.value)} size="md" />
              <Button loading={busy} w={{ base: '100%', sm: 'fit-content' }} onClick={() => void saveProfile()}>
                Сохранить профиль
              </Button>
            </Stack>
          </Surface>
        </Tabs.Panel>

        <Tabs.Panel value="security">
          <Surface style={{ maxWidth: 560 }}>
            <Stack gap="md">
              <Text fw={600}>Смена пароля</Text>
              <PasswordInput label="Текущий пароль" value={oldPass} onChange={(e) => setOldPass(e.currentTarget.value)} />
              <PasswordInput label="Новый пароль" value={newPass} onChange={(e) => setNewPass(e.currentTarget.value)} />
              <Button loading={busy} onClick={() => void changePassword()} disabled={newPass.length < 8}>
                Обновить пароль
              </Button>

              <Text fw={600} mt="md">
                Двухфакторная аутентификация (TOTP)
              </Text>
              {twoFa?.owner_2fa_required && (
                <Badge color="orange">Для Owner 2FA обязательна</Badge>
              )}
              <Text size="sm" c="#6d6c77">
                Статус: {twoFa?.totp_enabled || me?.totp_enabled ? 'включена' : 'выключена'}
              </Text>
              {!twoFa?.totp_enabled && !me?.totp_enabled && (
                <Button loading={busy} variant="light" onClick={() => void start2fa()}>
                  Включить 2FA
                </Button>
              )}
              {setup && (
                <Stack gap="sm">
                  {setup.qr_data_url && (
                    <Image src={setup.qr_data_url} alt="QR 2FA" maw={180} />
                  )}
                  <Code>{setup.secret}</Code>
                  <TextInput
                    label="Код из Authenticator"
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.currentTarget.value)}
                    maxLength={8}
                  />
                  <Button loading={busy} onClick={() => void confirm2fa()}>
                    Подтвердить 2FA
                  </Button>
                </Stack>
              )}
            </Stack>
          </Surface>
        </Tabs.Panel>

        <Tabs.Panel value="notifications">
          <Surface style={{ maxWidth: 560 }}>
            <Stack gap="md">
              <Switch
                label="Маркетинговые рассылки"
                checked={marketing}
                onChange={(e) => setMarketing(e.currentTarget.checked)}
              />
              {Object.entries(PREF_LABELS).map(([key, label]) => (
                <Checkbox
                  key={key}
                  label={label}
                  checked={prefs[key] ?? true}
                  onChange={(e) => setPrefs({ ...prefs, [key]: e.currentTarget.checked })}
                />
              ))}
              <Button loading={busy} w={{ base: '100%', sm: 'fit-content' }} onClick={() => void savePrefs()}>
                Сохранить уведомления
              </Button>
            </Stack>
          </Surface>
        </Tabs.Panel>

        <Tabs.Panel value="danger">
          <Surface style={{ maxWidth: 560 }}>
            <Stack gap="md">
              <Text fw={700} c="red">
                Удаление аккаунта
              </Text>
              <Text size="sm" c="#6d6c77">
                Право на забвение: заявка исполняется через 30 дней.
              </Text>
              <Button color="red" variant="light" onClick={() => void deleteAccount()}>
                Удалить аккаунт
              </Button>
            </Stack>
          </Surface>
        </Tabs.Panel>
      </Tabs>
    </SellerShell>
  );
}
