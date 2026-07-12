'use client';

import { Badge, Center, Loader, Stack, Text, Title } from '@mantine/core';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export default function ShareViewerPage() {
  const params = useParams<{ hash: string }>();
  const hash = params.hash;
  const [url, setUrl] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API}/models/share/${hash}`);
        if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);
        const data = (await res.json()) as { preview_url: string };
        setUrl(data.preview_url);
      } catch (e) {
        setErr(e instanceof Error ? e.message : 'Ошибка');
      } finally {
        setLoading(false);
      }
    })();
  }, [hash]);

  return (
    <Center mih="100vh" p="md" style={{ background: 'linear-gradient(160deg, #e8f4f3 0%, #f7f8fb 55%, #fff 100%)' }}>
      <Stack maw={1100} w="100%" gap="md">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title order={2}>3DVektor</Title>
            <Text c="dimmed" size="sm">
              Публичная ссылка /share/{hash}
            </Text>
          </div>
          <Badge color="teal">Share</Badge>
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
            <model-viewer
              src={url}
              camera-controls
              auto-rotate
              touch-action="pan-y"
              style={{ width: '100%', height: 560, background: 'transparent' }}
            />
          ) : (
            <Center h={560}>
              <Text c="dimmed">{err || 'Ссылка недействительна'}</Text>
            </Center>
          )}
        </div>
      </Stack>
    </Center>
  );
}

declare global {
  namespace JSX {
    interface IntrinsicElements {
      'model-viewer': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        src?: string;
        'camera-controls'?: boolean;
        'auto-rotate'?: boolean;
        'touch-action'?: string;
      };
    }
  }
}
