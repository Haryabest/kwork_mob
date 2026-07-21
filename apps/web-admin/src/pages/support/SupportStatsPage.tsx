import { Card, Center, Loader, SimpleGrid, Text } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';
import { MetricGrid, PageHeader, ShellTable } from '../../components/Panel';
import { api, getApiError } from '../../services/api';

type SupportStats = {
  total_tickets: number;
  open_tickets: number;
  answered_tickets: number;
  tickets_7d: number;
  avg_first_response_sec: number | null;
  agents: Array<{ agent_id: number | null; email: string | null; replies: number }>;
};

function fmtDuration(sec: number | null): string {
  if (sec == null) return '—';
  if (sec < 60) return `${sec} с`;
  const min = Math.round(sec / 60);
  if (min < 60) return `${min} мин`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return `${h} ч ${m} мин`;
}

export default function SupportStatsPage() {
  const [stats, setStats] = useState<SupportStats | null>(null);
  const [ollama, setOllama] = useState<{ ok?: boolean; model?: string } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get<SupportStats>('/admin/support/stats'),
      api.get<{ ok?: boolean; model?: string }>('/admin/support/ollama/status').catch(() => ({ data: null })),
    ])
      .then(([statsRes, ollamaRes]) => {
        setStats(statsRes.data);
        setOllama(ollamaRes.data);
      })
      .catch((e) => notifications.show({ color: 'red', message: getApiError(e) }))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Center py="xl"><Loader color="brand" /></Center>;
  if (!stats) return <PageHeader title="Статистика поддержки" description="Нет данных" />;

  return (
    <>
      <PageHeader title="Статистика поддержки" description="SLA, нагрузка агентов и качество ответов (§11.9)" />
      <MetricGrid
        items={[
          { label: 'Всего обращений', value: String(stats.total_tickets) },
          { label: 'Открытые', value: String(stats.open_tickets), color: stats.open_tickets > 0 ? 'orange' : 'teal' },
          { label: 'Отвечено', value: String(stats.answered_tickets), color: 'teal' },
          { label: 'За 7 дней', value: String(stats.tickets_7d) },
          { label: 'Средний первый ответ', value: fmtDuration(stats.avg_first_response_sec) },
        ]}
      />
      <SimpleGrid cols={{ base: 1, md: 2 }} mt="md">
        <Card withBorder>
          <Text fw={600} mb="sm">Нагрузка по агентам</Text>
          <ShellTable
            headers={['Агент', 'Ответов']}
            rows={
              stats.agents.length
                ? stats.agents.map((a) => [a.email || `#${a.agent_id ?? '—'}`, String(a.replies)])
                : [['—', '0']]
            }
          />
        </Card>
        <Card withBorder>
          <Text fw={600}>SLA</Text>
          <Text c="dimmed" size="sm" mt="sm">
            Цель первого ответа в рабочие часы — ≤ 2 ч (§1.4).
          </Text>
          <Text mt="sm">
            Текущий средний первый ответ: <b>{fmtDuration(stats.avg_first_response_sec)}</b>
          </Text>
        </Card>
        <Card withBorder>
          <Text fw={600}>ИИ-помощник (Ollama)</Text>
          <Text size="sm" mt="sm" c={ollama?.ok ? 'teal' : 'orange'}>
            {ollama?.ok ? `Доступен · ${ollama.model ?? 'model'}` : 'Недоступен — проверьте OLLAMA_URL'}
          </Text>
          <Text size="xs" c="dimmed" mt="xs">
            Кнопка «Предложить ответ ИИ» в карточке обращения §11.6
          </Text>
        </Card>
      </SimpleGrid>
    </>
  );
}
