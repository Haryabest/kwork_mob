'use client';

import { Center, Loader, Text } from '@mantine/core';
import { useCallback, useEffect, useState } from 'react';

type Props = {
  src: string;
  height?: number;
  autoRotate?: boolean;
};

type ModelViewerEl = HTMLElement & { loaded?: boolean };

export function ModelViewer3D({ src, height = 320, autoRotate = false }: Props) {
  const [scriptReady, setScriptReady] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const [viewerEl, setViewerEl] = useState<ModelViewerEl | null>(null);

  useEffect(() => {
    if (typeof customElements === 'undefined') return;
    if (customElements.get('model-viewer')) {
      setScriptReady(true);
      return;
    }
    customElements
      .whenDefined('model-viewer')
      .then(() => setScriptReady(true))
      .catch(() => setFailed(true));
  }, []);

  useEffect(() => {
    setLoaded(false);
    setFailed(false);
  }, [src]);

  useEffect(() => {
    const el = viewerEl;
    if (!el || !src || !scriptReady) return;

    let done = false;
    const finishOk = () => {
      if (done) return;
      done = true;
      setLoaded(true);
    };
    const finishErr = () => {
      if (done) return;
      done = true;
      setFailed(true);
    };

    const onLoad = () => finishOk();
    const onError = () => finishErr();

    el.addEventListener('load', onLoad);
    el.addEventListener('error', onError);

    if (el.loaded) finishOk();

    const t = window.setTimeout(() => {
      if (el.loaded) finishOk();
      else if (!done) finishErr();
    }, 45000);

    return () => {
      window.clearTimeout(t);
      el.removeEventListener('load', onLoad);
      el.removeEventListener('error', onError);
    };
  }, [viewerEl, src, scriptReady]);

  const onViewerRef = useCallback((node: ModelViewerEl | null) => {
    setViewerEl(node);
  }, []);

  if (!scriptReady) {
    return (
      <Center h={height}>
        <Loader color="brand" size="sm" />
      </Center>
    );
  }

  if (failed && !loaded) {
    return (
      <Center h={height} style={{ background: 'rgba(0,87,184,0.04)', borderRadius: 12 }}>
        <Text c="#6d6c77" ta="center" px="md" size="sm">
          Не удалось отобразить GLB в браузере. Файл на сервере есть — попробуйте «Скачать GLB».
        </Text>
      </Center>
    );
  }

  return (
    <div style={{ position: 'relative', width: '100%', height }}>
      {!loaded && (
        <Center
          style={{
            position: 'absolute',
            inset: 0,
            zIndex: 1,
            background: 'rgba(0,87,184,0.04)',
            borderRadius: 12,
            pointerEvents: 'none',
          }}
        >
          <Loader color="brand" size="sm" />
          <Text size="sm" c="#6d6c77" ml="sm">
            Загрузка 3D…
          </Text>
        </Center>
      )}
      <model-viewer
        ref={onViewerRef}
        src={src}
        camera-controls=""
        {...(autoRotate ? { 'auto-rotate': '' } : {})}
        touch-action="pan-y"
        exposure="1"
        shadow-intensity="0.4"
        camera-orbit="0deg 75deg 120%"
        min-camera-orbit="auto auto 50%"
        max-camera-orbit="auto auto 200%"
        style={{
          width: '100%',
          height,
          background: 'rgba(0,87,184,0.04)',
          borderRadius: 12,
        }}
      />
    </div>
  );
}

declare global {
  namespace JSX {
    interface IntrinsicElements {
      'model-viewer': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        src?: string;
        'camera-controls'?: string | boolean;
        'auto-rotate'?: string | boolean;
        'touch-action'?: string;
        exposure?: string;
        'shadow-intensity'?: string;
        'camera-orbit'?: string;
        'min-camera-orbit'?: string;
        'max-camera-orbit'?: string;
      };
    }
  }
}
