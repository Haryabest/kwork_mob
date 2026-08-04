'use client';

import { Center, Loader, Text } from '@mantine/core';
import { useEffect, useRef, useState, type CSSProperties } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

type Props = {
  src: string;
  height?: number | string;
  autoRotate?: boolean;
  background?: string;
  borderRadius?: number | string;
};

function resolveMinHeight(height: number | string): number {
  if (typeof height === 'number' && Number.isFinite(height) && height > 0) return height;
  return 400;
}

function fitCameraToObject(
  camera: THREE.PerspectiveCamera,
  object: THREE.Object3D,
  controls: OrbitControls,
) {
  const box = new THREE.Box3().setFromObject(object);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z) || 1;
  const dist = maxDim * 1.85;
  camera.position.set(center.x + dist * 0.55, center.y + dist * 0.35, center.z + dist);
  camera.near = Math.max(dist / 100, 0.01);
  camera.far = dist * 100;
  camera.updateProjectionMatrix();
  controls.target.copy(center);
}

export function ModelViewer3D({
  src,
  height = 400,
  autoRotate = false,
  background = 'rgba(0,87,184,0.04)',
  borderRadius = 12,
}: Props) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [status, setStatus] = useState('Загрузка 3D…');
  const minH = resolveMinHeight(height);

  const wrapStyle: CSSProperties = {
    position: 'relative',
    width: '100%',
    height: typeof height === 'number' ? height : height,
    minHeight: minH,
    overflow: 'hidden',
    background,
    borderRadius,
  };

  useEffect(() => {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    if (!wrap || !canvas || !src) return;

    let disposed = false;
    let raf = 0;
    let renderer: THREE.WebGLRenderer | null = null;
    let controls: OrbitControls | null = null;
    let scene: THREE.Scene | null = null;
    let resizeObserver: ResizeObserver | null = null;

    setFailed(false);
    setReady(false);
    setStatus('Подготовка области…');

    const boot = () => {
      if (disposed) return;

      const w0 = Math.max(64, Math.floor(wrap.clientWidth || wrap.getBoundingClientRect().width || 320));
      const h0 = Math.max(
        64,
        Math.floor(wrap.clientHeight || wrap.getBoundingClientRect().height || minH),
      );

      // Размер canvas ДО WebGL context — иначе "Attachment has zero size"
      canvas.width = w0;
      canvas.height = h0;
      canvas.style.width = '100%';
      canvas.style.height = '100%';
      canvas.style.display = 'block';

      try {
        renderer = new THREE.WebGLRenderer({
          canvas,
          antialias: true,
          alpha: true,
          powerPreference: 'high-performance',
        });
      } catch (e) {
        console.error('[ModelViewer3D] WebGL', e);
        setFailed(true);
        return;
      }

      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.setSize(w0, h0, false);
      renderer.outputColorSpace = THREE.SRGBColorSpace;

      scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(45, w0 / h0, 0.01, 1000);
      camera.position.set(1.5, 1.1, 2.2);

      scene.add(new THREE.AmbientLight(0xffffff, 0.85));
      const key = new THREE.DirectionalLight(0xffffff, 1.05);
      key.position.set(3, 5, 2);
      const fill = new THREE.DirectionalLight(0xffffff, 0.35);
      fill.position.set(-2, 1, -1);
      scene.add(key, fill);

      controls = new OrbitControls(camera, canvas);
      controls.enableDamping = true;
      controls.autoRotate = autoRotate;
      controls.autoRotateSpeed = 1.2;

      const applySize = () => {
        if (!renderer || disposed) return;
        const w = Math.max(64, Math.floor(wrap.clientWidth || 0));
        const h = Math.max(64, Math.floor(wrap.clientHeight || minH));
        if (w < 64 || h < 64) return;
        canvas.width = w;
        canvas.height = h;
        renderer.setSize(w, h, false);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
      };

      resizeObserver = new ResizeObserver(() => requestAnimationFrame(applySize));
      resizeObserver.observe(wrap);
      applySize();

      setStatus('Загрузка GLB…');
      const loader = new GLTFLoader();
      loader.load(
        src,
        (gltf) => {
          if (disposed || !scene || !controls) return;
          scene.add(gltf.scene);
          fitCameraToObject(camera, gltf.scene, controls);
          controls.update();
          setReady(true);
          setStatus('');
        },
        undefined,
        (err) => {
          console.error('[ModelViewer3D] GLB', err);
          if (!disposed) setFailed(true);
        },
      );

      const tick = () => {
        if (disposed || !renderer || !scene || !controls) return;
        controls.update();
        renderer.render(scene, camera);
        raf = window.requestAnimationFrame(tick);
      };
      tick();
    };

    // Дождаться layout (иначе clientWidth=0 на первом тике)
    const t0 = window.setTimeout(boot, 0);

    return () => {
      disposed = true;
      window.clearTimeout(t0);
      window.cancelAnimationFrame(raf);
      resizeObserver?.disconnect();
      controls?.dispose();
      if (renderer) {
        renderer.dispose();
        renderer.forceContextLoss();
      }
      scene?.traverse((obj) => {
        const mesh = obj as THREE.Mesh;
        mesh.geometry?.dispose?.();
        const mat = mesh.material;
        if (Array.isArray(mat)) mat.forEach((m) => m.dispose?.());
        else if (mat) (mat as THREE.Material).dispose?.();
      });
    };
  }, [src, autoRotate, minH]);

  return (
    <div ref={wrapRef} style={wrapStyle}>
      <canvas
        ref={canvasRef}
        width={640}
        height={400}
        style={{
          display: 'block',
          width: '100%',
          height: '100%',
          borderRadius,
        }}
      />
      {(!ready || failed) && (
        <Center
          style={{
            position: 'absolute',
            inset: 0,
            zIndex: 1,
            background,
            borderRadius,
            pointerEvents: failed ? 'auto' : 'none',
          }}
        >
          {failed ? (
            <Text c="#6d6c77" ta="center" px="md" size="sm">
              Не удалось отобразить GLB в браузере. Файл на сервере есть — попробуйте «Скачать GLB».
            </Text>
          ) : (
            <>
              <Loader color="brand" size="sm" />
              <Text size="sm" c="#6d6c77" ml="sm">
                {status || 'Загрузка 3D…'}
              </Text>
            </>
          )}
        </Center>
      )}
    </div>
  );
}
