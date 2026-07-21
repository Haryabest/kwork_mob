import { useCallback, useEffect, useState } from 'react';
import { Button, Card, Center, Group, Loader, Stack, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { PageHeader, ShellTable } from '../components/Panel';
import { api, getApiError } from '../services/api';

type Period = { prefix: string; keys: string[]; has_manifest?: boolean };

export default function AuditExportPage() {
  const [items, setItems] = useState<Period[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<{ items: Period[] }>('/admin/audit-export/periods');
      setItems(data.items ?? []);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function runExport() {
    setRunning(true);
    try {
      await api.post('/admin/audit-export/run');
      notifications.show({ color: 'teal', message: 'Экспорт выполнен' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setRunning(false);
    }
  }

  async function download(prefix: string, filename: string) {
    try {
      const { data } = await api.get<{ download_url?: string }>(
        `/admin/audit-export/periods/${prefix}/presign`,
        { params: { filename } },
      );
      if (data.download_url) window.open(data.download_url, '_blank');
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  if (loading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  return (
    <Stack gap="lg">
      <PageHeader
        title="Audit export"
        description="Ежемесячный экспорт audit/access в MinIO §10.5"
        action={
          <Group>
            <Button variant="light" onClick={() => void load()}>
              Обновить
            </Button>
            <Button loading={running} onClick={() => void runExport()}>
              Экспорт сейчас
            </Button>
          </Group>
        }
      />
      <Card withBorder>
        <ShellTable
          headers={['Период', 'Файлы', 'Действия']}
          rows={
            items.length
              ? items.map((p) => [
                  p.prefix,
                  String(p.keys?.length ?? 0),
                  <Group gap="xs" key={p.prefix}>
                    <Button size="xs" variant="light" onClick={() => void download(p.prefix, 'audit_log.csv.gz')}>
                      audit
                    </Button>
                    <Button size="xs" variant="light" onClick={() => void download(p.prefix, 'access_log.csv.gz')}>
                      access
                    </Button>
                    <Button size="xs" variant="light" onClick={() => void download(p.prefix, 'manifest.json')}>
                      manifest
                    </Button>
                  </Group>,
                ])
              : [['—', 'Нет экспортов', '—']]
          }
        />
      </Card>
    </Stack>
  );
}
