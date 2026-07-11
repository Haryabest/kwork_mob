'use client';

import { SellerShell } from '../../components/SellerShell';
import { Button, Card, Group, Modal, NumberInput, Select, Stack, Table, Tabs, Text, Title } from '@mantine/core';
import { IconDownload, IconPlus } from '@tabler/icons-react';
import { useDisclosure } from '@mantine/hooks';

export default function BalancePage() {
  const [opened, { open, close }] = useDisclosure(false);
  return (
    <SellerShell>
      <Title order={2} mb="xs">
        Баланс и пополнение
      </Title>
      <Text c="dimmed" size="sm" mb="lg">
        СБП + ЮKassa (§8.12)
      </Text>
      <Card withBorder padding="lg" radius="md">
        <Stack>
          <Group justify="space-between">
            <div>
              <Text size="sm" c="dimmed">
                Текущий баланс
              </Text>
              <Text fw={700} size="xl">
                0 ₽
              </Text>
            </div>
            <Button leftSection={<IconPlus size={16} />} onClick={open}>Пополнить</Button>
          </Group>
          <Group justify="space-between"><Text fw={600}>История транзакций</Text><Button variant="subtle" leftSection={<IconDownload size={16} />}>Экспорт CSV</Button></Group>
          <Group grow><Select label="Тип операции" placeholder="Все" data={['Пополнение', 'Списание', 'Возврат']} clearable /><Select label="Период" placeholder="За всё время" data={['Сегодня', 'Неделя', 'Месяц']} clearable /></Group>
          <Table><Table.Thead><Table.Tr><Table.Th>Дата</Table.Th><Table.Th>Тип</Table.Th><Table.Th>Сумма</Table.Th><Table.Th>Описание</Table.Th><Table.Th>Статус</Table.Th></Table.Tr></Table.Thead><Table.Tbody><Table.Tr><Table.Td colSpan={5}><Text ta="center" c="dimmed" py="lg">Транзакций пока нет</Text></Table.Td></Table.Tr></Table.Tbody></Table>
        </Stack>
      </Card>
      <Modal opened={opened} onClose={close} title="Пополнить баланс" centered>
        <Tabs defaultValue="sbp"><Tabs.List><Tabs.Tab value="sbp">СБП</Tabs.Tab><Tabs.Tab value="card">Банковская карта</Tabs.Tab></Tabs.List>
          <Tabs.Panel value="sbp" pt="md"><Stack><NumberInput label="Сумма, ₽" min={100} max={500000} defaultValue={100} /><Text size="sm" c="dimmed">Минимальная сумма — 100 ₽</Text><Button>Сгенерировать QR-код</Button></Stack></Tabs.Panel>
          <Tabs.Panel value="card" pt="md"><Stack><NumberInput label="Сумма, ₽" min={100} max={500000} defaultValue={100} /><Button>Перейти к оплате</Button></Stack></Tabs.Panel>
        </Tabs>
      </Modal>
    </SellerShell>
  );
}
