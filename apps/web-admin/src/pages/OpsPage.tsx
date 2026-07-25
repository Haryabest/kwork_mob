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
        message: `В очереди ${data.enqueued} за ${data.elapsed_sec}с`,
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
        title="Операции / критерии готовности"
        description="§1.4 КПЭ · переключение высокой доступности · mesh · TRELLIS · Debezium · нагрузочный тест"
        action={
          <Group>
            <Button leftSection={<IconDownload size={16} />} variant="light" onClick={() => void exportDod()}>
              Экспорт критериев CSV
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
            label: 'Критерии §1.4',
            value: `${passed}/${total}`,
            color: dod?.summary.ready ? 'teal' : 'orange',
            hint: dod?.summary.ready ? 'готово' : 'нужна проверка staging',
          },
          {
            label: 'Переключение ВД',
            value: cutover?.ready ? 'готово' : 'проверить',
            hint: `${cutover?.passed ?? '—'}/${cutover?.total ?? '—'} проверок`,
          },
          {
            label: 'TRELLIS онлайн',
            value: String(trellis?.trellis_online ?? 0),
            hint: trellis?.production_ready ? 'продакшн готов' : 'нет GPU-воркера',
          },
          {
            label: 'VIP-адрес MinIO',
            value: vip?.ok ? 'в норме' : '—',
            hint: String(vip?.vip ?? vip?.active_endpoint ?? 'не настроен'),
          },
        ]}
      />

      <SimpleGrid cols={{ base: 1, md: 2 }} mt="md">
        <div className="vz-surface">
          <Text fw={600} mb="sm">
            Проверки критериев готовности
          </Text>
          <Progress value={(passed / total) * 100} mb="md" color={dod?.summary.ready ? 'teal' : 'orange'} />
          <ShellTable
            headers={['Метрика', 'Значение', 'Результат']}
            rows={(dod?.checks ?? []).map((c) => [
              c.metric,
              String(c.value ?? '—'),
              <Badge key={c.metric} color={c.pass ? 'teal' : 'red'} variant="light">
                {c.pass ? 'в норме' : 'сбой'}
              </Badge>,
            ])}
          />
        </div>

        <Stack>
          <div className="vz-surface">
            <Text fw={600} mb="sm">
              HA / инфраструктура
            </Text>
            <Text size="sm">Mesh онлайн: {String(mesh?.online ?? '—')}/{String(mesh?.total ?? '—')}</Text>
            <Text size="sm">Debezium: {debezium?.configured ? (debezium?.ok ? 'РАБОТАЕТ' : 'недоступен') : 'не настроен'}</Text>
            <Text size="sm" c="dimmed" mt="xs">
              Режим синхронизации: {String(debezium?.sync_mode ?? 'celery')}
            </Text>
          </div>

          <div className="vz-surface">
            <Text fw={600} mb="sm">
              Нагрузочный тест §1.4
            </Text>
            <Group align="flex-end">
              <NumberInput label="Заказы" value={loadCount} onChange={setLoadCount} min={1} max={500} maw={120} />
              <Button loading={loadBusy} onClick={() => void runLoadTest()}>
                В очередь
              </Button>
            </Group>
          </div>

          <div className="vz-surface">
            <Text fw={600} mb="sm">
              TRELLIS-воркеры
            </Text>
            <ShellTable
              headers={['ID', 'Статус', 'TRELLIS', 'Онлайн']}
              rows={((trellis?.workers as Array<Record<string, unknown>>) ?? []).map((w) => [
                String(w.worker_id),
                String(w.status),
                w.has_trellis ? 'да' : 'нет',
                w.online ? 'да' : 'нет',
              ])}
            />
          </div>
        </Stack>
      </SimpleGrid>
    </>
  );
}
