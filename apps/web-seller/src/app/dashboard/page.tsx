'use client';

import { Button, Group, Stack, Text, Title, Skeleton, Image } from '@mantine/core';
import { IconBox, IconCash, IconCamera, IconUsers, IconShoppingCart } from '@tabler/icons-react';
import Link from 'next/link';
import { SellerShell } from '../../components/SellerShell';
import { EmptyState, PageHeader, Surface } from '../../components/ui';
import { useDashboard } from '../../hooks/useDashboard';

export default function DashboardPage() {
  const { data, isLoading: loading } = useDashboard();
  const me = data?.me ?? null;
  const orders = data?.orders ?? [];
  const models = data?.models ?? [];
  const company = data?.company ?? null;
  const thumbByUuid = data?.thumbByUuid ?? {};

  const activeOrders = orders.filter((o) => ['queued', 'processing', 'awaiting_payment', 'pending'].includes(o.status)).length;
  const monthSpend = orders
    .filter((o) => o.status !== 'cancelled' && o.status !== 'failed')
    .reduce((s, o) => s + Math.abs(o.amount || 0), 0);

  const stats = [
    { label: 'Баланс', value: me ? `${me.balance.toLocaleString('ru-RU')} ₽` : '—', Icon: IconCash },
    { label: 'Генераций', value: String(models.length || orders.filter((o) => o.status === 'completed').length), Icon: IconBox },
    { label: 'Активных заказов', value: String(activeOrders), Icon: IconShoppingCart },
    { label: 'Потрачено', value: `${monthSpend.toLocaleString('ru-RU')} ₽`, Icon: IconCash },
  ];

  const ownerStats =
    company?.is_owner || company?.role === 'owner'
      ? [
          { label: 'Команда', value: data?.teamCount != null ? String(data.teamCount) : '—', Icon: IconUsers },
          {
            label: 'Баланс компании',
            value: company.balance != null ? `${company.balance.toLocaleString('ru-RU')} ₽` : '—',
            Icon: IconCash,
          },
        ]
      : [];

  return (
    <SellerShell>
      <PageHeader
        title={me?.full_name ? `Здравствуйте, ${me.full_name.split(' ')[0]}` : 'Главная'}
        description="Баланс, статистика и быстрый старт генерации 3D-моделей"
        action={
          <Button component={Link} href="/orders/new" leftSection={<IconCamera size={16} />}>
            Снять товар
          </Button>
        }
      />

      <div
        style={{
          display: 'grid',
          gap: '1.35rem',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        }}
      >
        {loading
          ? Array.from({ length: 4 }).map((_, i) => (
              <Surface key={i}>
                <Skeleton height={12} width="40%" mb="md" />
                <Skeleton height={28} width="55%" />
              </Surface>
            ))
          : [...stats, ...ownerStats].map(({ label, value, Icon }) => (
              <Surface key={label}>
                <Group justify="space-between" align="flex-start" wrap="nowrap">
                  <div>
                    <Text size="sm" c="#6d6c77">
                      {label}
                    </Text>
                    <Text fw={700} size="xl" mt={10} className="vz-metric-value">
                      {value}
                    </Text>
                  </div>
                  <Icon size={20} color="#0057b8" stroke={1.55} />
                </Group>
              </Surface>
            ))}
      </div>

      <div
        style={{
          display: 'grid',
          gap: '1.5rem',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          marginTop: '1.5rem',
        }}
      >
        <Surface>
          <Group justify="space-between" mb="md" wrap="wrap">
            <div>
              <Title order={4}>Последние модели</Title>
              <Text size="sm" c="#6d6c77">
                До 5 последних генераций
              </Text>
            </div>
            <Button component={Link} href="/models" variant="subtle" size="compact-md">
              Смотреть все
            </Button>
          </Group>
          {models.length === 0 ? (
            <EmptyState
              title="Пока нет моделей"
              hint="Загрузите 12 ракурсов или снимите товар в мобильном приложении"
              actionLabel="Новый заказ"
              actionHref="/orders/new"
            />
          ) : (
            <Stack gap="sm">
              {models.slice(0, 5).map((m) => (
                <Group
                  key={m.uuid}
                  justify="space-between"
                  p="sm"
                  style={{
                    borderRadius: 12,
                    background: 'rgba(0,87,184,0.04)',
                  }}
                  wrap="nowrap"
                >
                  <Group gap="sm" wrap="nowrap">
                    {thumbByUuid[m.uuid] ? (
                      <Image src={thumbByUuid[m.uuid]!} alt="" w={48} h={48} radius="md" fit="cover" />
                    ) : (
                      <div
                        style={{
                          width: 48,
                          height: 48,
                          borderRadius: 8,
                          background: 'rgba(0,87,184,0.08)',
                        }}
                      />
                    )}
                    <div>
                      <Text fw={600} size="sm">
                        {m.display_name || `${m.uuid.slice(0, 8)}…`}
                      </Text>
                      <Text size="xs" c="#6d6c77">
                        {m.publish_status || 'not_published'}
                      </Text>
                    </div>
                  </Group>
                  <Button component={Link} href={`/models/${m.uuid}`} size="xs" variant="light">
                    Открыть
                  </Button>
                </Group>
              ))}
            </Stack>
          )}
        </Surface>

        <Surface>
          <Title order={4} mb="md">
            Быстрые действия
          </Title>
          <Stack gap="sm">
            <Button component={Link} href="/orders/new" leftSection={<IconCamera size={16} />} fullWidth>
              Снять товар / загрузить 12 фото
            </Button>
            <Button component={Link} href="/balance" variant="light" leftSection={<IconCash size={16} />} fullWidth>
              Пополнить баланс
            </Button>
            <Button component={Link} href="/team" variant="light" leftSection={<IconUsers size={16} />} fullWidth>
              Пригласить сотрудника
            </Button>
            <Button component={Link} href="/orders" variant="light" leftSection={<IconShoppingCart size={16} />} fullWidth>
              Мои заказы
            </Button>
          </Stack>
        </Surface>
      </div>
    </SellerShell>
  );
}
