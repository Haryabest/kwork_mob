'use client';

import { Image } from '@mantine/core';
import { useEffect, useState } from 'react';
import { api } from '../services/api';

export function ModelThumb({ uuid, size = 56 }: { uuid: string; size?: number }) {
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get<{ thumbnail_url?: string }>(`/models/${uuid}/thumbnail`)
      .then(({ data }) => {
        if (!cancelled) setSrc(data.thumbnail_url || null);
      })
      .catch(() => {
        if (!cancelled) setSrc(null);
      });
    return () => {
      cancelled = true;
    };
  }, [uuid]);

  if (!src) {
    return (
      <div
        aria-hidden
        style={{
          width: size,
          height: size,
          borderRadius: 8,
          background: 'rgba(0,87,184,0.08)',
          flexShrink: 0,
        }}
      />
    );
  }

  return (
    <Image
      src={src}
      alt=""
      w={size}
      h={size}
      radius="md"
      fit="contain"
      style={{ background: 'rgba(0,87,184,0.04)', flexShrink: 0 }}
    />
  );
}
