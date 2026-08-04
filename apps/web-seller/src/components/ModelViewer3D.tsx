'use client';

import { Center, Loader, Text } from '@mantine/core';
import { useCallback, useEffect, useRef, useState } from 'react';

type Props = {
  src: string;
  height?: number | string;
  autoRotate?: boolean;
  background?: string;
  borderRadius?: number | string;
};

type ModelViewerEl = HTMLElement & {
  loaded?: boolean;
  updateFraming?: () => void;
};

function resolveMinHeight(height: number | string): number {
  if (typeof height === 'number' && Number.isFinite(height)) return height;
  return 320;
}

export function ModelViewer3D({
  src,
  height = 320,
  autoRotate = false,
  background = 'rgba(0,87,184,0.04)',
  borderRadius = 12,
}: Props) {
  const [scriptReady, setScriptReady] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const [viewerEl, setViewerEl] = useState<ModelViewerEl | null>(null);
  const [box, setBox] = useState({ w: 0, h: 0 });
  const containerRef = useRef<HTMLDivElement | null>(null);
  const minH = resolveMinHeight(height);
  const sized = box.w >= 2 && box.h >= 2;

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
    const el = containerRef.current;
    if (!el) return;

    const measure = () => {
      const r = el.getBoundingClientRect();
      const w = Math.max(0, Math.floor(r.width));
      const h = Math.max(0, Math.floor(r.height));
      setBox((prev) => (prev.w === w && prev.h === h ? prev : { w, h }));
    };

    measure();
    const ro = new ResizeObserver(() => measure());
    ro.observe(el);
    window.addEventListener('resize', measure);
    // первый кадр после layout (часто 0×0 на mount)
    const raf = window.requestAnimationFrame(measure);
    const t = window.setTimeout(measure, 50);

    return () => {
      ro.disconnect();
      window.removeEventListener('resize', measure);
      window.cancelAnimationFrame(raf);
      window.clearTimeout(t);
    };
  }, [height, scriptReady]);

  useEffect(() => {
    const el = viewerEl;
    if (!el || !src || !scriptReady || !sized) return;

    let done = false;
    const finishOk = () => {
      if (done) return;
      done = true;
      setLoaded(true);
      try {
        el.updateFraming?.();
      } catch {
        /* ignore */
      }
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
  }, [viewerEl, src, scriptReady, sized]);

  const onViewerRef = useCallback((node: ModelViewerEl | null) => {
    setViewerEl(node);
  }, []);

  if (!scriptReady) {
    return (
      <Center h={typeof height === 'number' ? height : minH}>
        <Loader color="brand" size="sm" />
      </Center>
    );
  }

  if (failed && !loaded) {
    return (
      <Center h={typeof height === 'number' ? height : minH} style={{ background, borderRadius }}>
        <Text c="#6d6c77" ta="center" px="md" size="sm">
          Не удалось отобразить GLB в браузере. Файл на сервере есть — попробуйте «Скачать GLB».
        </Text>
      </Center>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        height,
        minHeight: typeof height === 'number' ? undefined : minH,
      }}
    >
      {(!loaded || !sized) && (
        <Center
          style={{
            position: 'absolute',
            inset: 0,
            zIndex: 1,
            background,
            borderRadius,
            pointerEvents: 'none',
          }}
        >
          <Loader color="brand" size="sm" />
          <Text size="sm" c="#6d6c77" ml="sm">
            Загрузка 3D…
          </Text>
        </Center>
      )}
      {sized ? (
        <model-viewer
          key={src}
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
            display: 'block',
            width: '100%',
            height: '100%',
            background,
            borderRadius,
          }}
        />
      ) : null}
    </div>
  );
}
