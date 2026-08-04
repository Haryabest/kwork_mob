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
  // canvas создаём сами в effect — React не должен трогать width/height (сброс WebGL)
  const hostRef = useRef<HTMLDivElement | null>(null);
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
    const host = hostRef.current;
    if (!wrap || !host || !src) return;

    let disposed = false;
    let raf = 0;
    let renderer: THREE.WebGLRenderer | null = null;
    let controls: OrbitControls | null = null;
    let scene: THREE.Scene | null = null;
    let camera: THREE.PerspectiveCamera | null = null;
    let resizeObserver: ResizeObserver | null = null;

    setFailed(false);
    setReady(false);
    setStatus('Подготовка области…');

    const canvas = document.createElement('canvas');
    canvas.style.display = 'block';
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.borderRadius = typeof borderRadius === 'number' ? `${borderRadius}px` : String(borderRadius);
    host.replaceChildren(canvas);

    const measure = () => {
      const w = Math.max(2, Math.floor(wrap.clientWidth || wrap.getBoundingClientRect().width || 0));
      const h = Math.max(
        2,
        Math.floor(wrap.clientHeight || wrap.getBoundingClientRect().height || 0),
      );
      return { w, h };
    };

    const waitForLayout = (): Promise<{ w: number; h: number }> =>
      new Promise((resolve) => {
        let tries = 0;
        const tick = () => {
          if (disposed) return;
          const { w, h } = measure();
          if (w >= 64 && h >= 64) {
            resolve({ w, h });
            return;
          }
          tries += 1;
          if (tries > 60) {
            resolve({ w: Math.max(w, 320), h: Math.max(h, minH) });
            return;
          }
          requestAnimationFrame(tick);
        };
        tick();
      });

    (async () => {
      const { w, h } = await waitForLayout();
      if (disposed) return;

      canvas.width = w;
      canvas.height = h;

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
      renderer.setSize(w, h, false);
      renderer.outputColorSpace = THREE.SRGBColorSpace;

      scene = new THREE.Scene();
      camera = new THREE.PerspectiveCamera(45, w / h, 0.01, 1000);
      camera.position.set(1.5, 1.1, 2.2);

      scene.add(new THREE.AmbientLight(0xffffff, 0.55));
      const hemi = new THREE.HemisphereLight(0xffffff, 0x444466, 0.65);
      hemi.position.set(0, 2, 0);
      scene.add(hemi);
      const key = new THREE.DirectionalLight(0xffffff, 1.15);
      key.position.set(3, 5, 2);
      const fill = new THREE.DirectionalLight(0xffffff, 0.45);
      fill.position.set(-2, 1, -1);
      const rim = new THREE.DirectionalLight(0xffffff, 0.35);
      rim.position.set(0, 2, -3);
      scene.add(key, fill, rim);

      controls = new OrbitControls(camera, canvas);
      controls.enableDamping = true;
      controls.autoRotate = autoRotate;
      controls.autoRotateSpeed = 1.2;

      const prepMaterials = (root: THREE.Object3D) => {
        root.traverse((obj) => {
          const mesh = obj as THREE.Mesh;
          if (!mesh.isMesh) return;
          const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
          for (const mat of mats) {
            if (!mat) continue;
            const std = mat as THREE.MeshStandardMaterial;
            if (std.map) std.map.colorSpace = THREE.SRGBColorSpace;
            if (std.emissiveMap) std.emissiveMap.colorSpace = THREE.SRGBColorSpace;
            std.side = THREE.DoubleSide;
            std.needsUpdate = true;
          }
        });
      };

      const applySize = () => {
        if (!renderer || !camera || disposed) return;
        const next = measure();
        if (next.w < 2 || next.h < 2) return; // не трогаем buffer нулём
        if (canvas.width === next.w && canvas.height === next.h) return;
        canvas.width = next.w;
        canvas.height = next.h;
        renderer.setSize(next.w, next.h, false);
        camera.aspect = next.w / next.h;
        camera.updateProjectionMatrix();
      };

      resizeObserver = new ResizeObserver(() => requestAnimationFrame(applySize));
      resizeObserver.observe(wrap);

      setStatus('Загрузка GLB…');
      const loader = new GLTFLoader();
      loader.load(
        src,
        (gltf) => {
          if (disposed || !scene || !controls || !camera) return;
          prepMaterials(gltf.scene);
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
        if (disposed || !renderer || !scene || !camera || !controls) return;
        // не рисуем в нулевой buffer
        if (canvas.width >= 2 && canvas.height >= 2) {
          controls.update();
          renderer.render(scene, camera);
        }
        raf = window.requestAnimationFrame(tick);
      };
      tick();
    })();

    return () => {
      disposed = true;
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
      host.replaceChildren();
    };
  }, [src, autoRotate, minH, borderRadius]);

  return (
    <div ref={wrapRef} style={wrapStyle} data-viewer="three-v2">
      <div ref={hostRef} style={{ width: '100%', height: '100%' }} />
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
