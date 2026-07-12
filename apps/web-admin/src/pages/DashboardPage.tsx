import { useState } from 'react';
import { Badge, Group, Progress, Text, Title } from '@mantine/core';
import {
  IconAlertTriangle,
  IconCash,
  IconClock,
  IconServer,
} from '@tabler/icons-react';

const STATS = [
  { label: 'В очереди', value: '42', icon: IconClock },
  { label: 'Воркеры online', value: '18 / 20', icon: IconServer },
  { label: 'Выручка сегодня', value: '84 230 ₽', icon: IconCash },
  { label: 'NSFW на проверке', value: '7', icon: IconAlertTriangle },
] as const;

const TABS = [
  {
    id: 'ops',
    label: 'Операции',
    cards: [
      { title: 'Очередь заказов', value: '42 задания', percent: 68 },
      { title: 'Среднее время выполнения', value: '2 мин 14 сек', percent: 45 },
    ],
  },
  {
    id: 'finance',
    label: 'Финансы',
    cards: [
      { title: 'Выручка за 7 дней', value: '528 400 ₽', percent: 74 },
      { title: 'Возвраты', value: '1.2%', percent: 12 },
    ],
  },
  {
    id: 'b2b',
    label: 'B2B',
    cards: [
      { title: 'Активные компании', value: '142', percent: 63 },
      { title: 'MRR B2B', value: '214 000 ₽', percent: 58 },
    ],
  },
  {
    id: 'quality',
    label: 'Качество',
    cards: [
      { title: 'Средний рейтинг', value: '4.8 / 5', percent: 96 },
      { title: 'Пересъёмки', value: '3.1%', percent: 31 },
    ],
  },
  {
    id: 'moderation',
    label: 'Модерация',
    cards: [
      { title: 'Проверено за сутки', value: '1 284', percent: 82 },
      { title: 'Отклонено', value: '7 материалов', percent: 7 },
    ],
  },
] as const;

export default function DashboardPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]['id']>('ops');
  const active = TABS.find((t) => t.id === tab) ?? TABS[0];

  return (
    <div className="vz-page">
      <div className="vz-page-header">
        <div>
          <Title order={2}>Дашборд</Title>
          <Text c="#6d6c77" size="sm" mt={6}>
            Очередь, EWT и загрузка GPU-воркеров
          </Text>
        </div>
        <Badge variant="light" color="brand" radius="sm">
          Live · ClickHouse
        </Badge>
      </div>

      <div className="vz-grid vz-grid-2 vz-grid-4">
        {STATS.map((s) => (
          <div key={s.label} className="vz-surface">
            <Group justify="space-between" align="flex-start" wrap="nowrap">
              <Text size="sm" c="#6d6c77">
                {s.label}
              </Text>
              <s.icon size={18} color="#0057b8" stroke={1.6} />
            </Group>
            <Text fw={700} size="xl" mt={14} className="vz-metric-value">
              {s.value}
            </Text>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.55rem' }}>
        {TABS.map((t) => {
          const on = t.id === tab;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              style={{
                border: on ? 'none' : '1px solid rgba(0,87,184,0.14)',
                background: on
                  ? 'linear-gradient(135deg, #0057b8 0%, #0381E9 45%, #9403fd 100%)'
                  : '#fff',
                color: on ? '#fff' : '#374151',
                borderRadius: 999,
                padding: '0.55rem 1.05rem',
                fontWeight: 600,
                fontSize: '0.875rem',
                cursor: 'pointer',
                minHeight: 44,
                fontFamily: 'inherit',
              }}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      <div className="vz-grid vz-grid-2-lg">
        {active.cards.map((c) => (
          <div key={c.title} className="vz-surface">
            <Text fw={600}>{c.title}</Text>
            <Text size="xl" fw={700} mt="lg" className="vz-metric-value">
              {c.value}
            </Text>
            <Progress value={c.percent} mt="lg" size="md" radius="xl" color="brand" />
          </div>
        ))}
      </div>
    </div>
  );
}
