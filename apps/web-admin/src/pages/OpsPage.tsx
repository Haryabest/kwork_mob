import { Badge, Button, Center, Group, Loader, NumberInput, Progress, SimpleGrid, Stack, Text } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconDownload, IconRefresh } from '@tabler/icons-react';
import { useCallback, useEffect, useState } from 'react';
import { MetricGrid, PageHeader, ShellTable } from '../components/Panel';
import { api, getApiError } from '../services/api';

type DodCheck = { metric: string; value: unknown; pass: boolean };
type DodData = {
  summary: { passed: number; total: number; ready: boolean };
  checks: DodCheck[];
  raw: Record<string, unknown>;
};

export default function OpsPage() {
  const [loading, setLoading] = useState(true);
  const [dod, setDod] = useState<DodData | null>(null);
  const [cutover, setCutover] = useState<Record<string, unknown> | null>(null);
  const [mesh, setMesh] = useState<Record<string, unknown> | null>(null);
  const [vip, setVip] = useState<Record<string, unknown> | null>(null);
  const [debezium, setDebezium] = useState<Record<string, unknown> | null>(null);
  const [trellis, setTrellis] = useState<Record<string, unknown> | null>(null);
  const [loadCount, setLoadCount] = useState<number | string>(100);
  const [loadBusy, setLoadBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [d, c, m, v, db, tr] = await Promise.all([
        api.get<DodData>('/admin/dod-metrics', { params: { days: 7 } }),
        api.get('/admin/ha/cutover/preflight'),
        api.get('/admin/ha/mesh'),
        api.get('/admin/ha/minio-vip'),
        api.get('/admin/monitoring/debezium'),
        api.get('/admin/worker/trellis-status'),
      ]);
      setDod(d.data);
      setCutover(c.data);
      setMesh(m.data);
      setVip(v.data);
      setDebezium(db.data);
      setTrellis(tr.data);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function exportDod() {
    try {
      const { data } = await api.get<Blob>('/admin/dod-metrics/export', {
        params: { days: 7 },
        responseType: 'blob',
      });
      const url = URL.createObjectURL(data);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'dod-metrics-7d.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  async function runLoadTest() {
    setLoadBusy(true);
    try {
      const { data } = await api.post<{ enqueued: number; elapsed_sec: number }>(
        '/admin/load-test/queue',
        null,
        { params: { count: Number(loadCount) || 100 } },
      );
      notifications.show({
        color: 'teal',
        message: `Enqueued ${data.enqueued} за ${data.elapsed_sec}s`,
      });
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setLoadBusy(false);
    }
  }

  if (loading && !dod) {
    return (
      <Center py="xl">
        <Loader color="brand" />
      </Center>
    );
  }

  const passed = dod?.summary.passed ?? 0;
  const total = dod?.summary.total ?? 1;

  return (
    <>
      <PageHeader
        title="Ops / DoD"
        description="§1.4 KPI · HA cutover · mesh · TRELLIS · Debezium · load test"
        action={
          <Group>
            <Button leftSection={<IconDownload size={16} />} variant="light" onClick={() => void exportDod()}>
              DoD CSV
            </Button>
            <Button leftSection={<IconRefresh size={16} />} variant="light" onClick={() => void load()}>
              Обновить
            </Button>
          </Group>
        }
      />

      <MetricGrid
        items={[
          {
            label: 'DoD §1.4',
            value: `${passed}/${total}`,
            color: dod?.summary.ready ? 'teal' : 'orange',
            hint: dod?.summary.ready ? 'ready' : 'needs staging verify',
          },
          {
            label: 'HA cutover',
            value: cutover?.ready ? 'ready' : 'check',
            hint: `${cutover?.passed ?? '—'}/${cutover?.total ?? '—'} checks`,
          },
          {
            label: 'TRELLIS online',
            value: String(trellis?.trellis_online ?? 0),
            hint: trellis?.production_ready ? 'prod ready' : 'no GPU worker',
          },
          {
            label: 'MinIO VIP',
            value: vip?.ok ? 'OK' : '—',
            hint: String(vip?.vip ?? vip?.active_endpoint ?? 'not configured'),
          },
        ]}
      />

      <SimpleGrid cols={{ base: 1, md: 2 }} mt="md">
        <div className="vz-surface">
          <Text fw={600} mb="sm">
            DoD checks
          </Text>
          <Progress value={(passed / total) * 100} mb="md" color={dod?.summary.ready ? 'teal' : 'orange'} />
          <ShellTable
            headers={['Метрика', 'Значение', 'Pass']}
            rows={(dod?.checks ?? []).map((c) => [
              c.metric,
              String(c.value ?? '—'),
              <Badge key={c.metric} color={c.pass ? 'teal' : 'red'} variant="light">
                {c.pass ? 'ok' : 'fail'}
              </Badge>,
            ])}
          />
        </div>

        <Stack>
          <div className="vz-surface">
            <Text fw={600} mb="sm">
              HA / Infra
            </Text>
            <Text size="sm">Mesh online: {String(mesh?.online ?? '—')}/{String(mesh?.total ?? '—')}</Text>
            <Text size="sm">Debezium: {debezium?.configured ? (debezium?.ok ? 'RUNNING' : 'down') : 'not configured'}</Text>
            <Text size="sm" c="dimmed" mt="xs">
              Sync mode: {String(debezium?.sync_mode ?? 'celery')}
            </Text>
          </div>

          <div className="vz-surface">
            <Text fw={600} mb="sm">
              Load test §1.4
            </Text>
            <Group align="flex-end">
              <NumberInput label="Orders" value={loadCount} onChange={setLoadCount} min={1} max={500} maw={120} />
              <Button loading={loadBusy} onClick={() => void runLoadTest()}>
                Enqueue
              </Button>
            </Group>
          </div>

          <div className="vz-surface">
            <Text fw={600} mb="sm">
              TRELLIS workers
            </Text>
            <ShellTable
              headers={['ID', 'Status', 'TRELLIS', 'Online']}
              rows={((trellis?.workers as Array<Record<string, unknown>>) ?? []).map((w) => [
                String(w.worker_id),
                String(w.status),
                w.has_trellis ? 'yes' : 'no',
                w.online ? 'yes' : 'no',
              ])}
            />
          </div>
        </Stack>
      </SimpleGrid>
    </>
  );
}
