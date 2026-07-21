import { useCallback, useEffect, useState } from 'react';
import { Badge, Button, Card, Center, Group, Loader, Progress, SimpleGrid, Text } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { MetricGrid, PageHeader, ShellTable } from '../components/Panel';
import { api, getApiError } from '../services/api';

type SegMetrics = {
  days: number;
  total: number;
  fallback_count: number;
  failed_count: number;
  fallback_rate: number;
  failed_rate: number;
  avg_confidence: number | null;
  by_device: Array<{ device_model: string; total: number; fallback: number; failed: number }>;
  by_method: Array<{ method: string; count: number }>;
  daily: Array<{ day: string | null; total: number; fallback: number }>;
};

export default function SegmentationPage() {
  const [data, setData] = useState<SegMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data: res } = await api.get<SegMetrics>('/admin/segmentation/metrics', { params: { days: 7 } });
      setData(res);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  const fallbackPct = Math.round((data?.fallback_rate ?? 0) * 100);
  const failedPct = Math.round((data?.failed_rate ?? 0) * 100);

  return (
    <>
      <PageHeader
        title="Сегментация"
        description="DeepLab/SAM fallback и failed §11.2.5"
        action={
          <Group>
            <Button variant="light" onClick={() => void load()}>
              Обновить
            </Button>
          </Group>
        }
      />
      <MetricGrid
        items={[
          { label: 'Событий (7д)', value: String(data?.total ?? 0) },
          { label: 'Fallback', value: `${fallbackPct}%`, color: fallbackPct > 15 ? 'orange' : 'teal' },
          { label: 'Failed', value: `${failedPct}%`, color: failedPct > 5 ? 'red' : 'teal' },
          {
            label: 'Avg confidence',
            value: data?.avg_confidence != null ? String(data.avg_confidence) : '—',
          },
        ]}
      />
      <SimpleGrid cols={{ base: 1, md: 2 }} mt="md">
        <Card withBorder>
          <Text fw={600} mb="sm">
            Fallback rate
          </Text>
          <Progress value={fallbackPct} color={fallbackPct > 15 ? 'orange' : 'brand'} />
          <Text size="sm" c="dimmed" mt="xs">
            Порог алерта: 15% / 24ч
          </Text>
        </Card>
        <Card withBorder>
          <Text fw={600} mb="sm">
            По методу
          </Text>
          <ShellTable
            headers={['Метод', 'Кол-во']}
            rows={
              data?.by_method?.length
                ? data.by_method.map((m) => [m.method || '—', String(m.count)])
                : [['—', '0']]
            }
          />
        </Card>
      </SimpleGrid>
      <Card withBorder mt="md">
        <Text fw={600} mb="sm">
          По устройству
        </Text>
        <ShellTable
          headers={['Устройство', 'Всего', 'Fallback', 'Failed']}
          rows={
            data?.by_device?.length
              ? data.by_device.map((d) => [
                  d.device_model,
                  String(d.total),
                  String(d.fallback),
                  String(d.failed),
                ])
              : [['—', '0', '0', '0']]
          }
        />
      </Card>
      {fallbackPct > 15 && (
        <Badge color="orange" mt="md">
          Fallback выше порога — проверьте segmentation_events
        </Badge>
      )}
    </>
  );
}
