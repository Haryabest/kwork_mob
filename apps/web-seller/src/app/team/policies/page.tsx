'use client';

import { Button, JsonInput, Stack, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';
import { SellerShell } from '../../../components/SellerShell';
import { api, apiMessage } from '../../../services/api';

export default function PoliciesPage() {
  const [raw, setRaw] = useState('{\n  "moderation_strict": false\n}');
  const [balance, setBalance] = useState<number | null>(null);

  useEffect(() => {
    api
      .get<{ settings: Record<string, unknown>; balance: number }>('/company/settings')
      .then(({ data }) => {
        setRaw(JSON.stringify(data.settings || {}, null, 2));
        setBalance(data.balance);
      })
      .catch((e) => notifications.show({ color: 'red', message: apiMessage(e) }));
  }, []);

  async function save() {
    try {
      const settings = JSON.parse(raw);
      await api.patch('/company/settings', { settings });
      notifications.show({ color: 'teal', message: 'Сохранено' });
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e, String(e)) });
    }
  }

  return (
    <SellerShell>
      <Title order={2} mb="xs">
        Политики компании
      </Title>
      <Text c="dimmed" size="sm" mb="md">
        Баланс компании: {balance != null ? `${balance} ₽` : '—'}
      </Text>
      <Stack maw={640}>
        <JsonInput label="settings JSON" value={raw} onChange={setRaw} minRows={10} formatOnBlur autosize />
        <Button w="fit-content" onClick={save}>
          Сохранить
        </Button>
      </Stack>
    </SellerShell>
  );
}
