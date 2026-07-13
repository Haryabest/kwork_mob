import { api } from '../services/api';

/** GLB для model-viewer через API (Bearer), без CORS MinIO. */
export async function loadModelPreviewBlobUrl(uuid: string): Promise<string | null> {
  const { data } = await api.get<ArrayBuffer>(`/models/${uuid}/preview/stream`, {
    responseType: 'arraybuffer',
  });
  if (!data || data.byteLength < 20) return null;
  const blob = new Blob([data], { type: 'model/gltf-binary' });
  return URL.createObjectURL(blob);
}

/** Отзыв blob URL при смене модели / unmount. */
export function revokeModelPreviewUrl(url: string | null | undefined) {
  if (url?.startsWith('blob:')) URL.revokeObjectURL(url);
}
