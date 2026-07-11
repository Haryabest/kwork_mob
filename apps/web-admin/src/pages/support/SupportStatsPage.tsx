import { Card, SimpleGrid, Text } from '@mantine/core';
import { MetricGrid, PageHeader, ShellTable, StateBadge } from '../../components/Panel';

export default function SupportStatsPage() {
  return <><PageHeader title="Статистика поддержки" description="SLA, нагрузка агентов и качество ответов" /><MetricGrid items={[{ label: 'Открытые тикеты', value: '24' }, { label: 'SLA соблюдено', value: '98.4%', color: 'teal' }, { label: 'Первый ответ', value: '8 мин' }, { label: 'CSAT', value: '4.7 / 5', color: 'teal' }]} /><SimpleGrid cols={{ base: 1, md: 2 }}><Card withBorder><Text fw={600}>Нагрузка по агентам</Text><Text c="dimmed" size="sm" mt="sm">График распределения обращений за 7 дней</Text></Card><Card withBorder><Text fw={600}>Темы обращений</Text><Text c="dimmed" size="sm" mt="sm">Оплата · Заказ · Модерация · B2B</Text></Card></SimpleGrid><ShellTable headers={['Агент', 'Тикетов', 'SLA', 'Статус']} rows={[['Анна Петрова', '18', '99%', <StateBadge value="Онлайн" color="teal" />]]} /></>;
}
