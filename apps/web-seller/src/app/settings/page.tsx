'use client';

import {
  Avatar,
  Badge,
  Button,
  Checkbox,
  Code,
  Group,
  Image,
  Modal,
  PasswordInput,
  Stack,
  Switch,
  Table,
  Tabs,
  Text,
  TextInput,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useCallback, useEffect, useState } from 'react';
import { SellerShell } from '../../components/SellerShell';
import { PageHeader, Surface } from '../../components/ui';
import {
  fetchOAuthProviders,
  oauthErrorMessage,
  resolveOAuthCompanyId,
  startOAuthLink,
  unlinkOAuth,
  type OAuthProvider,
} from '../../lib/oauth';
import { api, apiMessage } from '../../services/api';

type SessionItem = {
  id: number;
  created_at?: string | null;
  expires_at?: string | null;
};

type Me = {
  id: number;
  email: string;
  full_name?: string | null;
  phone?: string | null;
  avatar_url?: string | null;
  marketing_opt_in?: boolean;
  totp_enabled?: boolean;
  notification_prefs?: Record<string, boolean>;
  oauth_providers?: string[];
};

type TwoFaStatus = {
  totp_enabled: boolean;
  is_company_owner?: boolean;
  owner_2fa_required?: boolean;
};

type DeletionRequest = {
  active: boolean;
  status?: string;
  requested_at?: string | null;
  due_at?: string | null;
};

type OAuthAuditEntry = {
  user_id?: number;
  details?: { provider?: string };
  created_at?: string | null;
};

async function loadLastOAuthUnlink(isOwner: boolean): Promise<{
  item: OAuthAuditEntry | null;
  scope: 'company' | 'personal' | null;
}> {
  const params = { action: 'oauth_unlink', limit: 1 };
  if (isOwner) {
    try {
      const { data } = await api.get<{ items: OAuthAuditEntry[] }>('/company/audit', { params });
      const item = data.items?.[0] ?? null;
      if (item) return { item, scope: 'company' };
    } catch {
      /* not owner or no access */
    }
  }
  try {
    const { data } = await api.get<{ items: OAuthAuditEntry[] }>('/user/audit', { params });
    const item = data.items?.[0] ?? null;
    return { item, scope: item ? 'personal' : null };
  } catch {
    return { item: null, scope: null };
  }
}

async function loadLastOAuthLogin(): Promise<OAuthAuditEntry | null> {
  try {
    const { data } = await api.get<{ items: OAuthAuditEntry[] }>('/user/audit', {
      params: { action: 'oauth_login', limit: 1 },
    });
    return data.items?.[0] ?? null;
  } catch {
    return null;
  }
}

async function refreshOAuthHints(isOwner: boolean): Promise<{
  unlink: OAuthAuditEntry | null;
  unlinkScope: 'company' | 'personal' | null;
  login: OAuthAuditEntry | null;
}> {
  const unlinkData = await loadLastOAuthUnlink(isOwner);
  const login = await loadLastOAuthLogin();
  return { unlink: unlinkData.item, unlinkScope: unlinkData.scope, login };
}

const PREF_LABELS: Record<string, string> = {
  push_enabled: 'Push-уведомления',
  email_enabled: 'Email-уведомления',
  generation_done: 'Генерация готова',
  refund: 'Возврат средств',
  nsfw_blocked: 'NSFW-блокировка',
  source_expire: 'Истечение исходников',
  cleanup: 'Очистка хранилища',
  publish_reminder: 'Напоминание опубликовать',
  topup_failed: 'Ошибка пополнения',
  support_reply: 'Ответ поддержки',
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
  const [disableCode, setDisableCode] = useState('');
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [oauthProviders, setOauthProviders] = useState<OAuthProvider[]>([]);
  const [lastOAuthUnlink, setLastOAuthUnlink] = useState<OAuthAuditEntry | null>(null);
  const [lastOAuthLogin, setLastOAuthLogin] = useState<OAuthAuditEntry | null>(null);
  const [oauthUnlinkScope, setOauthUnlinkScope] = useState<'company' | 'personal' | null>(null);
  const [oauthCompanyId, setOauthCompanyId] = useState<number | undefined>(undefined);
  const [accessLogRows, setAccessLogRows] = useState<
    Array<{ id: number; model_uuid: string; action?: string; file_format?: string; timestamp?: string }>
  >([]);
  const [pushDevices, setPushDevices] = useState<
    Array<{ id: number; platform?: string; app_version?: string; token_prefix?: string; updated_at?: string }>
  >([]);
  const [draftBackups, setDraftBackups] = useState<
    Array<{ model_uuid: string; category?: string; captured_count?: number; uploaded_at?: string; expires_at?: string }>
  >([]);
  const [busy, setBusy] = useState(false);
  const [deletion, setDeletion] = useState<DeletionRequest | null>(null);
  const [deleteModal, setDeleteModal] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState('');
  const oauthLinkedProviders = me?.oauth_providers ?? [];

  const loadSessions = useCallback(async () => {
    try {
      const { data } = await api.get<{ items: SessionItem[] }>('/auth/sessions');
      setSessions(data.items ?? []);
    } catch {
      /* сессии не критичны для остальной страницы */
    }
  }, []);

  const load = useCallback(async () => {
    const cachedMe =
      typeof window !== 'undefined' ? sessionStorage.getItem('oauth_link_me') : null;
    if (cachedMe) sessionStorage.removeItem('oauth_link_me');
    const mePromise = cachedMe
      ? Promise.resolve({ data: JSON.parse(cachedMe) as Me })
      : api.get<Me>('/user/me');
    const [m, s] = await Promise.all([mePromise, api.get<TwoFaStatus>('/auth/2fa/status')]);
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
      topup_failed: true,
      support_reply: true,
      email_orders: true,
      email_balance: true,
      ...(m.data.notification_prefs || {}),
    });
    setTwoFa(s.data);
    void loadSessions();
    try {
      setOauthProviders(await fetchOAuthProviders());
    } catch {
      setOauthProviders([]);
    }
    setOauthCompanyId(await resolveOAuthCompanyId());
    const hints = await refreshOAuthHints(Boolean(s.data.is_company_owner));
    setLastOAuthUnlink(hints.unlink);
    setOauthUnlinkScope(hints.unlinkScope);
    setLastOAuthLogin(hints.login);
    if (cachedMe) {
      const afterLink = await refreshOAuthHints(Boolean(s.data.is_company_owner));
      setLastOAuthUnlink(afterLink.unlink);
      setOauthUnlinkScope(afterLink.unlinkScope);
      setLastOAuthLogin(afterLink.login);
    }
    try {
      const { data: del } = await api.get<DeletionRequest>('/user/me/deletion-request');
      setDeletion(del);
    } catch {
      setDeletion(null);
    }
    try {
      const { data } = await api.get<{
        items: Array<{ id: number; model_uuid: string; action?: string; file_format?: string; timestamp?: string }>;
      }>('/user/access-log', { params: { limit: 20 } });
      setAccessLogRows(data.items ?? []);
    } catch {
      setAccessLogRows([]);
    }
    try {
      const { data } = await api.get<{ items: typeof pushDevices }>('/user/devices');
      setPushDevices(data.items ?? []);
    } catch {
      setPushDevices([]);
    }
    try {
      const { data } = await api.get<{ items: typeof draftBackups; ttl_days?: number }>('/user/draft-backups');
      setDraftBackups(data.items ?? []);
    } catch {
      setDraftBackups([]);
    }
  }, [loadSessions]);

  useEffect(() => {
    load().catch((e) => notifications.show({ color: 'red', message: apiMessage(e) }));
  }, [load]);

  async function revokePushDevice(id: number) {
    setBusy(true);
    try {
      await api.delete(`/user/devices/${id}`);
      const { data } = await api.get<{ items: typeof pushDevices }>('/user/devices');
      setPushDevices(data.items ?? []);
      notifications.show({ color: 'teal', message: 'Устройство отвязано' });
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function deleteDraftBackup(modelUuid: string) {
    setBusy(true);
    try {
      await api.delete(`/user/draft-backups/${modelUuid}`);
      const { data } = await api.get<{ items: typeof draftBackups }>('/user/draft-backups');
      setDraftBackups(data.items ?? []);
      notifications.show({ color: 'teal', message: 'Черновик удалён' });
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function unlinkOAuthProvider(provider: string) {
    setBusy(true);
    try {
      await unlinkOAuth(provider, oauthCompanyId);
      const { data } = await api.get<Me>('/user/me');
      setMe(data);
      const hints = await refreshOAuthHints(Boolean(twoFa?.is_company_owner));
      setLastOAuthUnlink(hints.unlink);
      setOauthUnlinkScope(hints.unlinkScope);
      setLastOAuthLogin(hints.login);
      notifications.show({ color: 'teal', message: 'Соцсеть отвязана' });
    } catch (error) {
      notifications.show({ color: 'red', message: oauthErrorMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  async function linkOAuth(provider: string) {
    setBusy(true);
    try {
      await startOAuthLink(provider, oauthCompanyId);
    } catch (error) {
      notifications.show({ color: 'red', message: oauthErrorMessage(error) });
      setBusy(false);
    }
  }

  async function exportUserAuditCsv() {
    setBusy(true);
    try {
      const { data } = await api.get('/user/audit/export', {
        params: { action_prefix: 'oauth_' },
        responseType: 'blob',
      });
      const url = URL.createObjectURL(data);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'user_audit.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      notifications.show({ color: 'red', message: apiMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  async function uploadAvatar(file: File) {
    setBusy(true);
    try {
      const form = new FormData();
      form.append('file', file);
      await api.post('/user/me/avatar', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      notifications.show({ color: 'teal', message: 'Аватар обновлён' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function deleteAvatar() {
    setBusy(true);
    try {
      await api.delete('/user/me/avatar');
      notifications.show({ color: 'teal', message: 'Аватар удалён' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

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

  async function disable2fa() {
    setBusy(true);
    try {
      await api.post('/auth/2fa/disable', { code: disableCode.trim() });
      setDisableCode('');
      notifications.show({ color: 'teal', message: '2FA отключена' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function revokeSession(id: number) {
    try {
      await api.delete(`/auth/sessions/${id}`);
      notifications.show({ color: 'teal', message: 'Сессия завершена' });
      await loadSessions();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }

  async function revokeOtherSessions() {
    try {
      const { data } = await api.post<{ revoked: number }>('/auth/sessions/revoke-others', {});
      notifications.show({ color: 'teal', message: `Завершено сессий: ${data.revoked}` });
      await loadSessions();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }

  async function deleteAccount() {
    if (deleteConfirm.trim().toUpperCase() !== 'УДАЛИТЬ') {
      notifications.show({ color: 'orange', message: 'Введите УДАЛИТЬ для подтверждения' });
      return;
    }
    setBusy(true);
    try {
      const { data } = await api.post<{
        due_at?: string;
        message?: string;
      }>('/user/me/delete-request');
      setDeletion({
        active: true,
        status: 'pending',
        due_at: data.due_at ?? null,
        requested_at: new Date().toISOString(),
      });
      setDeleteModal(false);
      setDeleteConfirm('');
      notifications.show({ color: 'orange', message: data.message || 'Заявка на удаление создана' });
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
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
              <Group>
                <Avatar src={me?.avatar_url || undefined} radius="xl" size={72}>
                  {(me?.full_name || me?.email || '?').slice(0, 2).toUpperCase()}
                </Avatar>
                <Stack gap={4}>
                  <Button
                    component="label"
                    variant="light"
                    size="xs"
                    loading={busy}
                  >
                    Загрузить фото
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      hidden
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) void uploadAvatar(file);
                        e.target.value = '';
                      }}
                    />
                  </Button>
                  {me?.avatar_url ? (
                    <Button variant="subtle" size="xs" color="red" loading={busy} onClick={() => void deleteAvatar()}>
                      Удалить
                    </Button>
                  ) : null}
                </Stack>
              </Group>
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
              {(twoFa?.totp_enabled || me?.totp_enabled) && !twoFa?.owner_2fa_required && (
                <Stack gap="sm">
                  <TextInput
                    label="Код для отключения 2FA"
                    value={disableCode}
                    onChange={(e) => setDisableCode(e.currentTarget.value)}
                    maxLength={8}
                  />
                  <Button
                    color="red"
                    variant="light"
                    loading={busy}
                    disabled={disableCode.trim().length < 6}
                    onClick={() => void disable2fa()}
                  >
                    Отключить 2FA
                  </Button>
                </Stack>
              )}

              <Text fw={600} mt="md">
                Вход через соцсети
              </Text>
              <Text size="sm" c="#6d6c77">
                Привяжите VK ID, Яндекс ID или Сбер ID для быстрого входа.
              </Text>
              {lastOAuthLogin && (
                <Text size="xs" c="dimmed">
                  Последний вход через соцсеть: {lastOAuthLogin.details?.provider ?? '—'}
                  {lastOAuthLogin.created_at
                    ? ` · ${new Date(lastOAuthLogin.created_at).toLocaleString('ru-RU')}`
                    : ''}
                </Text>
              )}
              {lastOAuthUnlink && (
                <Text size="xs" c="dimmed">
                  {oauthUnlinkScope === 'company' ? 'Последняя отвязка в компании' : 'Последняя отвязка'}:{' '}
                  {lastOAuthUnlink.details?.provider ?? '—'}
                  {lastOAuthUnlink.created_at
                    ? ` · ${new Date(lastOAuthUnlink.created_at).toLocaleString('ru-RU')}`
                    : ''}
                </Text>
              )}
              {oauthProviders.length === 0 ? (
                <Text size="sm" c="dimmed">
                  OAuth не настроен на сервере
                </Text>
              ) : (
                <Stack gap="xs">
                  {oauthProviders.map((p) => {
                    const linked = oauthLinkedProviders.includes(p.provider);
                    return (
                      <Group key={p.provider} justify="space-between">
                        <Text size="sm">{p.label}</Text>
                        {linked ? (
                          <Group gap="xs">
                            <Badge color="teal">Привязан</Badge>
                            <Button
                              size="xs"
                              variant="subtle"
                              color="red"
                              loading={busy}
                              onClick={() => void unlinkOAuthProvider(p.provider)}
                            >
                              Отвязать
                            </Button>
                          </Group>
                        ) : (
                          <Button size="xs" variant="light" loading={busy} onClick={() => void linkOAuth(p.provider)}>
                            Привязать
                          </Button>
                        )}
                      </Group>
                    );
                  })}
                </Stack>
              )}

              <Group justify="space-between" mt="md">
                <Text fw={600}>Личный аудит OAuth</Text>
                <Button size="xs" variant="light" loading={busy} onClick={() => void exportUserAuditCsv()}>
                  Export CSV
                </Button>
              </Group>
              <Text size="sm" c="#6d6c77">
                Скачать историю oauth_login / oauth_link / oauth_unlink.
              </Text>

              <Group justify="space-between" mt="md">
                <Text fw={600}>Скачивания моделей</Text>
                <Button
                  size="xs"
                  variant="light"
                  loading={busy}
                  onClick={async () => {
                    setBusy(true);
                    try {
                      const { data } = await api.get('/user/access-log/export', { responseType: 'blob' });
                      const url = URL.createObjectURL(data);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = 'user-access-log.csv';
                      a.click();
                      URL.revokeObjectURL(url);
                    } catch (error) {
                      notifications.show({ color: 'red', message: apiMessage(error) });
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Export CSV
                </Button>
              </Group>
              {accessLogRows.length === 0 ? (
                <Text size="sm" c="dimmed">
                  Пока нет скачиваний
                </Text>
              ) : (
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Когда</Table.Th>
                      <Table.Th>Модель</Table.Th>
                      <Table.Th>Действие</Table.Th>
                      <Table.Th>Формат</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {accessLogRows.map((r) => (
                      <Table.Tr key={r.id}>
                        <Table.Td>
                          {r.timestamp ? new Date(r.timestamp).toLocaleString('ru-RU') : '—'}
                        </Table.Td>
                        <Table.Td>{r.model_uuid?.slice(0, 8) ?? '—'}…</Table.Td>
                        <Table.Td>{r.action ?? '—'}</Table.Td>
                        <Table.Td>{r.file_format ?? '—'}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}

              <Text fw={600} mt="md">
                Активные сессии
              </Text>
              <Text size="sm" c="#6d6c77">
                Устройства с активным входом. Завершите незнакомые сессии.
              </Text>
              {sessions.length === 0 ? (
                <Text size="sm" c="dimmed">
                  Нет активных сессий
                </Text>
              ) : (
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Начало</Table.Th>
                      <Table.Th>Действует до</Table.Th>
                      <Table.Th />
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {sessions.map((s) => (
                      <Table.Tr key={s.id}>
                        <Table.Td>
                          {s.created_at ? new Date(s.created_at).toLocaleString('ru-RU') : '—'}
                        </Table.Td>
                        <Table.Td>
                          {s.expires_at ? new Date(s.expires_at).toLocaleDateString('ru-RU') : '—'}
                        </Table.Td>
                        <Table.Td>
                          <Button size="xs" variant="subtle" color="red" onClick={() => void revokeSession(s.id)}>
                            Завершить
                          </Button>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
              <Group>
                <Button variant="light" color="red" onClick={() => void revokeOtherSessions()}>
                  Завершить все, кроме текущей
                </Button>
              </Group>

              <Text fw={600} mt="md">
                Push-устройства
              </Text>
              <Text size="sm" c="#6d6c77">
                Зарегистрированные токены для уведомлений §2.5.5
              </Text>
              {pushDevices.length === 0 ? (
                <Text size="sm" c="dimmed">
                  Нет зарегистрированных устройств
                </Text>
              ) : (
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Платформа</Table.Th>
                      <Table.Th>Версия</Table.Th>
                      <Table.Th>Токен</Table.Th>
                      <Table.Th>Обновлено</Table.Th>
                      <Table.Th />
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {pushDevices.map((d) => (
                      <Table.Tr key={d.id}>
                        <Table.Td>{d.platform ?? '—'}</Table.Td>
                        <Table.Td>{d.app_version ?? '—'}</Table.Td>
                        <Table.Td>
                          <Text size="sm" ff="monospace">
                            {d.token_prefix ?? '—'}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          {d.updated_at ? new Date(d.updated_at).toLocaleString('ru-RU') : '—'}
                        </Table.Td>
                        <Table.Td>
                          <Button
                            size="xs"
                            variant="subtle"
                            color="red"
                            disabled={busy}
                            onClick={() => void revokePushDevice(d.id)}
                          >
                            Отвязать
                          </Button>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}

              <Text fw={600} mt="md">
                Облачные черновики
              </Text>
              <Text size="sm" c="#6d6c77">
                Бэкапы съёмки TTL 7 дней §3.3.2
              </Text>
              {draftBackups.length === 0 ? (
                <Text size="sm" c="dimmed">
                  Нет сохранённых черновиков
                </Text>
              ) : (
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Модель</Table.Th>
                      <Table.Th>Категория</Table.Th>
                      <Table.Th>Ракурсы</Table.Th>
                      <Table.Th>Истекает</Table.Th>
                      <Table.Th />
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {draftBackups.map((b) => (
                      <Table.Tr key={b.model_uuid}>
                        <Table.Td>
                          <Text size="sm" ff="monospace">
                            {b.model_uuid.slice(0, 8)}…
                          </Text>
                        </Table.Td>
                        <Table.Td>{b.category ?? '—'}</Table.Td>
                        <Table.Td>{b.captured_count ?? '—'}</Table.Td>
                        <Table.Td>{b.expires_at ? b.expires_at.slice(0, 10) : '—'}</Table.Td>
                        <Table.Td>
                          <Button
                            size="xs"
                            variant="subtle"
                            color="red"
                            disabled={busy}
                            onClick={() => void deleteDraftBackup(b.model_uuid)}
                          >
                            Удалить
                          </Button>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Stack>
          </Surface>
        </Tabs.Panel>

        <Tabs.Panel value="notifications">
          <Surface style={{ maxWidth: 560 }}>
            <Stack gap="md">
              <Switch
                label="Маркетинговые рассылки §20.8.3"
                description="Отписка от промо, кампаний и акций (marketing_opt_in). Транзакционные уведомления не отключаются."
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
                Право на забвение (§2.8.3): персональные данные удаляются в течение 30 дней. Финансовые
                записи анонимизируются и хранятся 5 лет.
              </Text>
              {deletion?.active ? (
                <Stack gap="xs">
                  <Badge color="orange">Заявка принята</Badge>
                  <Text size="sm">
                    Статус: {deletion.status ?? 'pending'}
                    {deletion.due_at
                      ? ` · исполнение до ${new Date(deletion.due_at).toLocaleDateString('ru-RU')}`
                      : ''}
                  </Text>
                </Stack>
              ) : (
                <Button color="red" variant="light" onClick={() => setDeleteModal(true)}>
                  Удалить аккаунт
                </Button>
              )}
            </Stack>
          </Surface>
        </Tabs.Panel>
      </Tabs>

      <Modal
        opened={deleteModal}
        onClose={() => {
          setDeleteModal(false);
          setDeleteConfirm('');
        }}
        title="Удалить аккаунт?"
        centered
      >
        <Stack gap="md">
          <Text size="sm">
            Это необратимо после исполнения заявки. Введите <strong>УДАЛИТЬ</strong> для подтверждения.
          </Text>
          <TextInput
            label="Подтверждение"
            placeholder="УДАЛИТЬ"
            value={deleteConfirm}
            onChange={(e) => setDeleteConfirm(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDeleteModal(false)}>
              Отмена
            </Button>
            <Button color="red" loading={busy} onClick={() => void deleteAccount()}>
              Подать заявку
            </Button>
          </Group>
        </Stack>
      </Modal>
    </SellerShell>
  );
}
