'use client';

import { Badge, Center, Loader, Stack, Text, Title } from '@mantine/core';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

type SharePayload = {
  preview_url: string;
  watermark?: string;
  no_download?: boolean;
};

export default function ShareViewerPage() {
  const params = useParams<{ hash: string }>();
  const hash = params.hash;
  const [data, setData] = useState<SharePayload | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API}/models/share/${hash}`);
        if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);
        setData((await res.json()) as SharePayload);
      } catch (e) {
        setErr(e instanceof Error ? e.message : 'Ошибка');
      } finally {
        setLoading(false);
      }
    })();
  }, [hash]);

  useEffect(() => {
    const block = (e: Event) => e.preventDefault();
    document.addEventListener('contextmenu', block);
    return () => document.removeEventListener('contextmenu', block);
  }, []);

  const url = data?.preview_url ?? null;
  const watermark = data?.watermark ?? '3DVektor';

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
            position: 'relative',
            minHeight: 560,
            borderRadius: 16,
            overflow: 'hidden',
            background: 'rgba(11,122,115,0.06)',
            border: '1px solid rgba(11,122,115,0.12)',
            userSelect: 'none',
          }}
        >
          {loading ? (
            <Center h={560}>
              <Loader color="teal" />
            </Center>
          ) : url ? (
            <>
              <model-viewer
                src={url}
                camera-controls
                auto-rotate
                touch-action="pan-y"
                style={{ width: '100%', height: 560, background: 'transparent', pointerEvents: 'auto' }}
              />
              <div
                aria-hidden
                style={{
                  position: 'absolute',
                  inset: 0,
                  pointerEvents: 'none',
                  backgroundImage:
                    'repeating-linear-gradient(-30deg, transparent, transparent 120px, rgba(11,122,115,0.06) 120px, rgba(11,122,115,0.06) 240px)',
                }}
              />
              <Text
                size="sm"
                fw={600}
                c="teal.8"
                style={{
                  position: 'absolute',
                  bottom: 16,
                  right: 16,
                  opacity: 0.75,
                  letterSpacing: 1,
                  textShadow: '0 1px 2px rgba(255,255,255,0.8)',
                }}
              >
                {watermark}
              </Text>
            </>
          ) : (
            <Center h={560}>
              <Text c="dimmed">{err || 'Ссылка недействительна'}</Text>
            </Center>
          )}
        </div>
        {data?.no_download ? (
          <Text size="xs" c="dimmed" ta="center">
            Просмотр только в браузере. Скачивание отключено.
          </Text>
        ) : null}
      </Stack>
    </Center>
  );
}
