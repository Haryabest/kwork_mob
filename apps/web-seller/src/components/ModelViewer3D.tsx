'use client';

import { Center, Loader, Text } from '@mantine/core';
import { useEffect, useRef, useState, type CSSProperties } from 'react';

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
  dismissPoster?: () => void;
};

function resolveMinHeight(height: number | string): number {
  if (typeof height === 'number' && Number.isFinite(height) && height > 0) return height;
  return 360;
}

export function ModelViewer3D({
  src,
  height = 360,
  autoRotate = false,
  background = 'rgba(0,87,184,0.04)',
  borderRadius = 12,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const viewerRef = useRef<ModelViewerEl | null>(null);
  const [scriptReady, setScriptReady] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const [box, setBox] = useState({ w: 0, h: 0 });
  const minH = resolveMinHeight(height);
  const sized = box.w >= 64 && box.h >= 64;

  // Контейнер всегда в DOM — иначе ResizeObserver не видит размер.
  const containerStyle: React.CSSProperties = {
    position: 'relative',
    width: '100%',
    height: typeof height === 'number' ? height : height,
    minHeight: minH,
    overflow: 'hidden',
    background,
    borderRadius,
  };

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
      // clientWidth надёжнее при transform/subpixel
      const w = Math.max(0, Math.floor(el.clientWidth || r.width));
      const h = Math.max(0, Math.floor(el.clientHeight || r.height));
      setBox((prev) => (prev.w === w && prev.h === h ? prev : { w, h }));
    };

    measure();
    const ro = new ResizeObserver(() => {
      // после layout
      requestAnimationFrame(measure);
    });
    ro.observe(el);
    window.addEventListener('resize', measure);
    const t1 = window.setTimeout(measure, 0);
    const t2 = window.setTimeout(measure, 100);
    const t3 = window.setTimeout(measure, 300);

    return () => {
      ro.disconnect();
      window.removeEventListener('resize', measure);
      window.clearTimeout(t1);
      window.clearTimeout(t2);
      window.clearTimeout(t3);
    };
  }, [height]);

  // Явные px на host + resize после появления
  useEffect(() => {
    const el = viewerRef.current;
    if (!el || !sized) return;
    el.style.width = `${box.w}px`;
    el.style.height = `${box.h}px`;
    el.style.maxWidth = '100%';
    el.style.display = 'block';
    try {
      el.updateFraming?.();
    } catch {
      /* ignore */
    }
    window.dispatchEvent(new Event('resize'));
  }, [box.w, box.h, sized, src]);

  useEffect(() => {
    const el = viewerRef.current;
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
  }, [src, scriptReady, sized, box.w, box.h]);

  return (
    <div ref={containerRef} style={containerStyle}>
      {(!scriptReady || !sized || !loaded) && !failed && (
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
            {!scriptReady ? 'Инициализация 3D…' : !sized ? 'Подготовка области…' : 'Загрузка GLB…'}
          </Text>
        </Center>
      )}

      {failed && !loaded && (
        <Center style={{ position: 'absolute', inset: 0, zIndex: 2, background, borderRadius }}>
          <Text c="#6d6c77" ta="center" px="md" size="sm">
            Не удалось отобразить GLB в браузере. Файл на сервере есть — попробуйте «Скачать GLB».
          </Text>
        </Center>
      )}

      {/* src только после ненулевого размера — иначе WebGL canvas 0×0 */}
      {scriptReady && sized ? (
        <model-viewer
          ref={(node) => {
            viewerRef.current = node as ModelViewerEl | null;
          }}
          // eslint-disable-next-line react/no-unknown-property
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
            width: box.w,
            height: box.h,
            maxWidth: '100%',
            background: 'transparent',
            borderRadius,
          }}
        />
      ) : null}
    </div>
  );
}
