import { useCallback, useEffect, useState } from 'react';
import { Button, Card, Center, Group, Loader, Stack, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { api, getApiError } from '../services/api';

export default function GrafanaPage() {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<{ embed_url: string | null; configured: boolean }>(
        '/admin/grafana/embed',
      );
      setUrl(data.embed_url);
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

  return (
    <div className="vz-page">
      <Group justify="space-between" mb="md">
        <div>
          <Title order={2}>Grafana</Title>
          <Text c="#6d6c77" size="sm">
            Мониторинг §11.1 — задайте GRAFANA_EMBED_URL
          </Text>
        </div>
        <Button variant="light" onClick={() => void load()}>
          Обновить
        </Button>
      </Group>
      {url ? (
        <iframe
          title="Grafana"
          src={url}
          style={{ width: '100%', height: 'calc(100vh - 140px)', border: 0, borderRadius: 8 }}
        />
      ) : (
        <Card withBorder p="lg">
          <Text>Grafana embed URL не настроен (GRAFANA_EMBED_URL).</Text>
        </Card>
      )}
    </div>
  );
}
