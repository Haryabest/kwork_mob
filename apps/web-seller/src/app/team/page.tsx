'use client';

import {
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  CopyButton,
  ActionIcon,
  Tooltip,
  Textarea,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconCheck, IconCopy, IconLink, IconUserPlus } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { useCallback, useEffect, useState } from 'react';
import { SellerShell } from '../../components/SellerShell';
import { EmptyState, FilterRow, PageHeader, ScrollTable, SubNav, Surface } from '../../components/ui';
import { api, apiMessage } from '../../services/api';

type Member = {
  user_id: number;
  email?: string | null;
  full_name?: string | null;
  role: string;
};
type Invite = {
  id: number;
  email: string;
  role: string;
  status: string;
  url: string;
  expires_at?: string;
};

/** §20.5 Команда + shoot_link Owner */
export default function TeamPage() {
  const [inviteOpen, inviteHandlers] = useDisclosure(false);
  const [shootOpen, shootHandlers] = useDisclosure(false);
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<string | null>('photographer');
  const [limitOrders, setLimitOrders] = useState<number | string>(3);
  const [limitSpend, setLimitSpend] = useState<number | string>('');
  const [ttl, setTtl] = useState<string | null>('7');
  const [busy, setBusy] = useState(false);
  const [shootUrl, setShootUrl] = useState<string | null>(null);
  const [shootCategory, setShootCategory] = useState<string | null>('other');
  const [shootTier, setShootTier] = useState<string | null>('small');

  const load = useCallback(async () => {
    try {
      const [m, i] = await Promise.all([
        api.get<{ items: Member[] }>('/company/members'),
        api.get<{ items: Invite[] }>('/company/invitations'),
      ]);
      setMembers(m.data.items ?? []);
      setInvites(i.data.items ?? []);
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function sendInvite() {
    if (!email || !role) return;
    setBusy(true);
    try {
      const { data } = await api.post<{ url: string }>('/company/invite', {
        email,
        role,
        max_concurrent_orders: typeof limitOrders === 'number' ? limitOrders : Number(limitOrders) || 3,
        monthly_spending_limit:
          limitSpend === '' || limitSpend == null
            ? null
            : typeof limitSpend === 'number'
              ? limitSpend
              : Number(limitSpend),
        ttl_days: Number(ttl || 7),
      });
      notifications.show({ color: 'teal', message: `Приглашение создано: ${data.url}` });
      inviteHandlers.close();
      setEmail('');
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function createShootLink() {
    setBusy(true);
    try {
      const { data } = await api.post<{ url: string }>('/company/shoot_link', {
        category: shootCategory,
        tier: shootTier,
        ttl_hours: 48,
        max_uses: 1,
      });
      setShootUrl(data.url);
      notifications.show({ color: 'teal', message: 'Ссылка для фотографа создана' });
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <SellerShell>
      <PageHeader
        title="Команда и доступы"
        description="Приглашения, роли, лимиты и съёмка по ссылке для внештатных фотографов"
        action={
          <Group gap="sm">
            <Button variant="light" leftSection={<IconLink size={16} />} onClick={shootHandlers.open}>
              Ссылка на съёмку
            </Button>
            <Button leftSection={<IconUserPlus size={16} />} onClick={inviteHandlers.open}>
              Пригласить
            </Button>
          </Group>
        }
      />

      <SubNav
        items={[
          { href: '/team/roles', label: 'Роли' },
          { href: '/team/policies', label: 'Политики' },
          { href: '/team/audit', label: 'Аудит' },
          { href: '/team/sessions', label: 'Сессии' },
          { href: '/team/api-keys', label: 'API-ключи' },
        ]}
      />

      <Surface>
        <FilterRow>
          <TextInput label="Поиск" placeholder="Имя или email" disabled />
          <Select
            label="Роль"
            placeholder="Все роли"
            data={['owner', 'manager', 'photographer', 'viewer']}
            clearable
            disabled
          />
        </FilterRow>
        <ScrollTable>
          <Table miw={720} verticalSpacing="md">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Сотрудник</Table.Th>
                <Table.Th>Роль</Table.Th>
                <Table.Th>Email</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {members.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={3}>
                    <EmptyState
                      title="В команде пока никого нет"
                      hint="Отправьте приглашение — сотрудник получит ссылку на email"
                    />
                  </Table.Td>
                </Table.Tr>
              ) : (
                members.map((m) => (
                  <Table.Tr key={m.user_id}>
                    <Table.Td fw={600}>{m.full_name || `User #${m.user_id}`}</Table.Td>
                    <Table.Td>{m.role}</Table.Td>
                    <Table.Td>{m.email}</Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </ScrollTable>
      </Surface>

      <Surface>
        <Text fw={700} mb="md">
          Исходящие приглашения
        </Text>
        {invites.length === 0 ? (
          <EmptyState title="Приглашений нет" />
        ) : (
          <ScrollTable>
            <Table miw={640} verticalSpacing="md">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Email</Table.Th>
                  <Table.Th>Роль</Table.Th>
                  <Table.Th>Статус</Table.Th>
                  <Table.Th>Ссылка</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {invites.map((inv) => (
                  <Table.Tr key={inv.id}>
                    <Table.Td>{inv.email}</Table.Td>
                    <Table.Td>{inv.role}</Table.Td>
                    <Table.Td>{inv.status}</Table.Td>
                    <Table.Td>
                      <Group gap={6} wrap="nowrap">
                        <Text size="sm" lineClamp={1} maw={220}>
                          {inv.url}
                        </Text>
                        <CopyButton value={inv.url}>
                          {({ copied, copy }) => (
                            <Tooltip label={copied ? 'Скопировано' : 'Копировать'}>
                              <ActionIcon variant="light" onClick={copy}>
                                {copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
                              </ActionIcon>
                            </Tooltip>
                          )}
                        </CopyButton>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </ScrollTable>
        )}
      </Surface>

      <Modal opened={inviteOpen} onClose={inviteHandlers.close} title="Пригласить сотрудника" centered radius="lg" padding="lg">
        <Stack gap="md">
          <Text size="sm" c="#6d6c77">
            Owner сохраняет контроль над балансом. Сотрудник входит по ссылке.
          </Text>
          <TextInput label="Email" type="email" required size="md" value={email} onChange={(e) => setEmail(e.currentTarget.value)} />
          <Select
            label="Роль"
            data={[
              { value: 'manager', label: 'Manager' },
              { value: 'photographer', label: 'Photographer' },
              { value: 'viewer', label: 'Viewer' },
            ]}
            value={role}
            onChange={setRole}
            size="md"
          />
          <NumberInput label="Лимит активных заказов" min={1} value={limitOrders} onChange={setLimitOrders} size="md" />
          <NumberInput label="Лимит расходов в месяц, ₽" min={0} value={limitSpend} onChange={setLimitSpend} size="md" />
          <Select label="Срок" data={[{ value: '1', label: '1 день' }, { value: '7', label: '7 дней' }, { value: '30', label: '30 дней' }]} value={ttl} onChange={setTtl} size="md" />
          <Button fullWidth loading={busy} onClick={() => void sendInvite()}>
            Создать приглашение
          </Button>
        </Stack>
      </Modal>

      <Modal opened={shootOpen} onClose={shootHandlers.close} title="Ссылка на съёмку" centered radius="lg" padding="lg" size="lg">
        <Stack gap="md">
          <Text size="sm" c="#6d6c77">
            Внештатный фотограф загрузит 12 ракурсов без регистрации (§3 / §20).
          </Text>
          <Select
            label="Категория"
            value={shootCategory}
            onChange={setShootCategory}
            data={[
              { value: 'clothing', label: 'Одежда' },
              { value: 'shoes', label: 'Обувь' },
              { value: 'electronics', label: 'Электроника' },
              { value: 'other', label: 'Другое' },
            ]}
          />
          <Select
            label="Тариф"
            value={shootTier}
            onChange={setShootTier}
            data={[
              { value: 'small', label: 'Small' },
              { value: 'large', label: 'Large' },
            ]}
          />
          <Button loading={busy} onClick={() => void createShootLink()}>
            Сгенерировать ссылку
          </Button>
          {shootUrl && (
            <Textarea label="Ссылка" value={shootUrl} readOnly minRows={2} />
          )}
          {shootUrl && (
            <CopyButton value={shootUrl}>
              {({ copied, copy }) => (
                <Button variant="light" leftSection={copied ? <IconCheck size={16} /> : <IconCopy size={16} />} onClick={copy}>
                  {copied ? 'Скопировано' : 'Копировать'}
                </Button>
              )}
            </CopyButton>
          )}
        </Stack>
      </Modal>
    </SellerShell>
  );
}
