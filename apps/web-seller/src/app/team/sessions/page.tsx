'use client';

import { Button, Group, Select, Stack, Table, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';
import { SellerShell } from '../../../components/SellerShell';
import { api, apiMessage } from '../../../services/api';

type Member = { user_id: number; email?: string };
type Session = { id: number; jti: string; revoked: boolean; expires_at?: string; created_at?: string };

export default function SessionsPage() {
  const [members, setMembers] = useState<Member[]>([]);
  const [userId, setUserId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);

  useEffect(() => {
    api
      .get<{ items: Member[] }>('/company/members')
      .then(({ data }) => setMembers(data.items ?? []))
      .catch((e) => notifications.show({ color: 'red', message: apiMessage(e) }));
  }, []);

  async function loadSessions(uid: string) {
    const { data } = await api.get<{ items: Session[] }>(`/company/members/${uid}/sessions`);
    setSessions(data.items ?? []);
  }

  async function revoke() {
    if (!userId) return;
    try {
      const { data } = await api.post<{ revoked: number }>(`/company/members/${userId}/sessions/revoke`);
      notifications.show({ color: 'teal', message: `Отозвано: ${data.revoked}` });
      await loadSessions(userId);
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }

  return (
    <SellerShell>
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>Сессии</Title>
          <Text c="dimmed" size="sm">
            Refresh-токены сотрудников
          </Text>
        </div>
        <Button color="red" variant="light" disabled={!userId} onClick={revoke}>
          Отозвать все
        </Button>
      </Group>
      <Select
        label="Сотрудник"
        mb="md"
        maw={360}
        value={userId}
        onChange={(v) => {
          setUserId(v);
          if (v) loadSessions(v).catch((e) => notifications.show({ color: 'red', message: apiMessage(e) }));
        }}
        data={members.map((m) => ({ value: String(m.user_id), label: m.email || String(m.user_id) }))}
      />
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>ID</Table.Th>
            <Table.Th>JTI</Table.Th>
            <Table.Th>Статус</Table.Th>
            <Table.Th>Создан</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {sessions.map((s) => (
            <Table.Tr key={s.id}>
              <Table.Td>{s.id}</Table.Td>
              <Table.Td>
                <code>{s.jti.slice(0, 8)}…</code>
              </Table.Td>
              <Table.Td>{s.revoked ? 'revoked' : 'active'}</Table.Td>
              <Table.Td>{s.created_at ?? '—'}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </SellerShell>
  );
}
