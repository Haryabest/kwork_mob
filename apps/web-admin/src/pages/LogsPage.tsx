import {
  Button,
  Center,
  Group,
  Loader,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { IconDownload, IconRefresh } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { useCallback, useEffect, useState } from 'react';
import { PageHeader, ShellTable, StateBadge } from '../components/Panel';
import { api, getApiError } from '../services/api';

type LogRow = {
  id?: string;
  timestamp: string;
  source: string;
  level: string;
  message: string;
  worker_id?: string | null;
  task_id?: string | null;
};

const SOURCE_OPTIONS = [
  { value: 'all', label: 'Все источники' },
  { value: 'worker', label: 'Воркер' },
  { value: 'api', label: 'API' },
  { value: 'audit', label: 'Аудит' },
  { value: 'orchestrator', label: 'Оркестратор' },
];

const LEVEL_OPTIONS = [
  { value: 'all', label: 'Все уровни' },
  { value: 'DEBUG', label: 'DEBUG' },
  { value: 'INFO', label: 'INFO' },
  { value: 'WARNING', label: 'WARNING' },
  { value: 'ERROR', label: 'ERROR' },
];

function levelColor(level: string) {
  const l = level.toUpperCase();
  if (l === 'ERROR') return 'red';
  if (l === 'WARNING') return 'orange';
  if (l === 'DEBUG') return 'gray';
  return 'blue';
}

function formatTs(iso: string) {
  try {
    return new Date(iso).toLocaleString('ru-RU');
  } catch {
    return iso;
  }
}

function downloadCsv(items: LogRow[]) {
  const header = ['timestamp', 'level', 'source', 'message', 'worker_id', 'task_id'];
  const lines = [
    header.join(','),
    ...items.map((r) =>
      [
        r.timestamp,
        r.level,
        r.source,
        `"${(r.message || '').replace(/"/g, '""')}"`,
        r.worker_id || '',
        r.task_id || '',
      ].join(','),
    ),
  ];
  const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `admin_logs_${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function LogsPage() {
  const [items, setItems] = useState<LogRow[]>([]);
  const [backend, setBackend] = useState('');
  const [loading, setLoading] = useState(true);
  const [source, setSource] = useState<string | null>('all');
  const [level, setLevel] = useState<string | null>('all');
  const [q, setQ] = useState('');
  const [searchQ, setSearchQ] = useState('');

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const { data } = await api.get<{
        items: LogRow[];
        backend: string;
      }>('/admin/logs', {
        params: {
          source: source === 'all' ? undefined : source,
          level: level === 'all' ? undefined : level,
          q: searchQ || undefined,
          limit: 200,
        },
      });
      setItems(data.items ?? []);
      setBackend(data.backend ?? '');
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      if (!silent) setLoading(false);
    }
  }, [source, level, searchQ]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const t = setInterval(() => load(true), 10_000);
    return () => clearInterval(t);
  }, [load]);

  async function exportServerCsv() {
    try {
      const { data } = await api.get('/admin/logs/export', {
        params: {
          source: source === 'all' ? undefined : source,
          level: level === 'all' ? undefined : level,
          q: searchQ || undefined,
          limit: 5000,
        },
        responseType: 'blob',
      });
      const url = URL.createObjectURL(data as Blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'admin_logs.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      downloadCsv(items);
      notifications.show({ color: 'yellow', message: `CSV fallback: ${getApiError(e)}` });
    }
  }

  return (
    <>
      <PageHeader
        title="Логи"
        description="Централизованный просмотр §11.5 · auto-refresh 10с"
        action={
          <Group>
            <Button leftSection={<IconRefresh size={16} />} variant="light" onClick={() => load()}>
              Обновить
            </Button>
            <Button leftSection={<IconDownload size={16} />} onClick={exportServerCsv}>
              CSV
            </Button>
          </Group>
        }
      />
      <Stack gap="md" mb="md">
        <Group grow align="flex-end">
          <Select label="Источник" data={SOURCE_OPTIONS} value={source} onChange={setSource} />
          <Select label="Уровень" data={LEVEL_OPTIONS} value={level} onChange={setLevel} />
          <TextInput
            label="Поиск"
            placeholder="текст, worker_id, task_id"
            value={q}
            onChange={(e) => setQ(e.currentTarget.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') setSearchQ(q.trim());
            }}
          />
          <Button onClick={() => setSearchQ(q.trim())}>Найти</Button>
        </Group>
        {backend && (
          <Text size="xs" c="dimmed">
            backend: {backend}
          </Text>
        )}
      </Stack>
      {loading ? (
        <Center py="xl">
          <Loader color="brand" />
        </Center>
      ) : (
        <ShellTable
          headers={['Время', 'Уровень', 'Источник', 'Сообщение', 'Воркер', 'Задача']}
          rows={
            items.length
              ? items.map((r) => [
                  formatTs(r.timestamp),
                  <StateBadge key={`l-${r.id}`} value={r.level} color={levelColor(r.level)} />,
                  r.source,
                  <Text key={`m-${r.id}`} size="sm" lineClamp={2} maw={420}>
                    {r.message}
                  </Text>,
                  r.worker_id || '—',
                  r.task_id || '—',
                ])
              : [['—', '—', '—', 'Нет записей за период', '—', '—']]
          }
        />
      )}
    </>
  );
}
