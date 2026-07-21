'use client';

import { Badge, Center, Loader, Stack, Text, Title } from '@mantine/core';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { ModelViewer3D } from '../../../components/ModelViewer3D';
import { apiMessage } from '../../../services/api';
import { loadModelPreviewBlobUrl, revokeModelPreviewUrl } from '../../../lib/modelPreview';

export default function ViewerPage() {
  const params = useParams<{ uuid: string }>();
  const uuid = params.uuid;
  const [url, setUrl] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let blobUrl: string | null = null;
    (async () => {
      try {
        blobUrl = await loadModelPreviewBlobUrl(uuid);
        if (blobUrl) setUrl(blobUrl);
        else setErr('GLB недоступен');
      } catch (e) {
        setErr(apiMessage(e));
      } finally {
        setLoading(false);
      }
    })();
    return () => revokeModelPreviewUrl(blobUrl);
  }, [uuid]);

  return (
    <Center mih="100vh" p="md" style={{ background: 'linear-gradient(160deg, #e8f4f3 0%, #f7f8fb 55%, #fff 100%)' }}>
      <Stack maw={1100} w="100%" gap="md">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title order={2}>3DVektor Viewer</Title>
            <Text c="dimmed" size="sm">
              Модель {uuid}
            </Text>
          </div>
          <Badge color="teal">Просмотр</Badge>
        </div>
        <div
          style={{
            minHeight: 560,
            borderRadius: 16,
            overflow: 'hidden',
            background: 'rgba(11,122,115,0.06)',
            border: '1px solid rgba(11,122,115,0.12)',
          }}
        >
          {loading ? (
            <Center h={560}>
              <Loader color="teal" />
            </Center>
          ) : url ? (
            <ModelViewer3D src={url} height={560} autoRotate />
          ) : (
            <Center h={560}>
              <Text c="dimmed">{err || 'GLB недоступен'}</Text>
            </Center>
          )}
        </div>
        <Text size="xs" c="dimmed" ta="center">
          3DVektor · интерактивный просмотр GLB
        </Text>
      </Stack>
    </Center>
  );
}
