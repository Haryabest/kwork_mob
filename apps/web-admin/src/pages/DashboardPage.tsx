import { Badge, Card, Group, SimpleGrid, Text, ThemeIcon, Title, Tabs, Progress } from '@mantine/core';
import {
  IconAlertTriangle,
  IconCash,
  IconClock,
  IconServer,
} from '@tabler/icons-react';

const STATS = [
  { label: 'В очереди', value: '42', icon: IconClock, color: 'blue' },
  { label: 'Воркеры online', value: '18 / 20', icon: IconServer, color: 'teal' },
  { label: 'Выручка сегодня', value: '84 230 ₽', icon: IconCash, color: 'brand' },
  { label: 'NSFW на проверке', value: '7', icon: IconAlertTriangle, color: 'orange' },
] as const;

export default function DashboardPage() {
  return (
    <>
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>Дашборд</Title>
          <Text c="dimmed" size="sm">
            Активные заказы, EWT, загрузка воркеров
          </Text>
        </div>
        <Badge variant="light" color="teal">
          ClickHouse · обновлено сейчас
        </Badge>
      </Group>

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
        {STATS.map((s) => (
          <Card key={s.label} shadow="sm" padding="lg" radius="md" withBorder>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                {s.label}
              </Text>
              <ThemeIcon variant="light" color={s.color} radius="md">
                <s.icon size={18} />
              </ThemeIcon>
            </Group>
            <Text fw={700} size="xl" mt="sm">
              {s.value}
            </Text>
          </Card>
        ))}
      </SimpleGrid>
      <Tabs defaultValue="ops" mt="lg">
        <Tabs.List>
          <Tabs.Tab value="ops">Операции</Tabs.Tab>
          <Tabs.Tab value="finance">Финансы</Tabs.Tab>
          <Tabs.Tab value="b2b">B2B</Tabs.Tab>
          <Tabs.Tab value="quality">Качество</Tabs.Tab>
          <Tabs.Tab value="moderation">Модерация</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="ops" pt="md"><SimpleGrid cols={{ base: 1, md: 2 }}><ChartCard title="Очередь заказов" value="42 задания" percent={68} /><ChartCard title="Среднее время выполнения" value="2 мин 14 сек" percent={45} /></SimpleGrid></Tabs.Panel>
        <Tabs.Panel value="finance" pt="md"><SimpleGrid cols={{ base: 1, md: 2 }}><ChartCard title="Выручка за 7 дней" value="528 400 ₽" percent={74} /><ChartCard title="Возвраты" value="1.2%" percent={12} /></SimpleGrid></Tabs.Panel>
        <Tabs.Panel value="b2b" pt="md"><SimpleGrid cols={{ base: 1, md: 2 }}><ChartCard title="Активные компании" value="142" percent={63} /><ChartCard title="MRR B2B" value="214 000 ₽" percent={58} /></SimpleGrid></Tabs.Panel>
        <Tabs.Panel value="quality" pt="md"><SimpleGrid cols={{ base: 1, md: 2 }}><ChartCard title="Средний рейтинг" value="4.8 / 5" percent={96} /><ChartCard title="Пересъёмки" value="3.1%" percent={31} /></SimpleGrid></Tabs.Panel>
        <Tabs.Panel value="moderation" pt="md"><SimpleGrid cols={{ base: 1, md: 2 }}><ChartCard title="Проверено за сутки" value="1 284" percent={82} /><ChartCard title="Отклонено" value="7 материалов" percent={7} /></SimpleGrid></Tabs.Panel>
      </Tabs>
    </>
  );
}

function ChartCard({ title, value, percent }: { title: string; value: string; percent: number }) {
  return <Card withBorder><Text fw={600}>{title}</Text><Text size="xl" fw={700} mt="md">{value}</Text><Progress value={percent} mt="md" /></Card>;
}
