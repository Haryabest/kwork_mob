import { api } from '../services/api';

export type PhotoPrepare = {
  task_uuid: string;
  photo_count: number;
  photos_prefix: string;
  uploads: { index: number; upload_url: string; key: string; content_type: string }[];
};

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** По одному файлу + retry — стабильнее на мобильном и медленном Wi‑Fi. */
export async function uploadOrderPhotosSequential(
  prep: PhotoPrepare,
  files: File[],
  onProgress?: (percent: number) => void,
): Promise<void> {
  const slots = prep.uploads;
  if (files.length !== slots.length) {
    throw new Error(`Ожидалось ${slots.length} фото, получено ${files.length}`);
  }
  const total = files.length;
  for (let i = 0; i < total; i++) {
    const slot = slots[i];
    const file = files[i];
    const form = new FormData();
    form.append('file', file);
    let lastErr: unknown;
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        await api.post(
          `/orders/photos/upload-slot?task_uuid=${encodeURIComponent(prep.task_uuid)}&view_index=${slot.index}`,
          form,
          {
            headers: { 'Content-Type': 'multipart/form-data' },
            timeout: 120_000,
          },
        );
        lastErr = undefined;
        break;
      } catch (e) {
        lastErr = e;
        if (attempt < 3) await sleep(1500 * attempt);
      }
    }
    if (lastErr) throw lastErr;
    if (onProgress) onProgress(Math.round(((i + 1) / total) * 80));
  }
  if (prep.photo_count !== 12) {
    await api.post(`/orders/photos/expand?task_uuid=${encodeURIComponent(prep.task_uuid)}`, null, {
      timeout: 60_000,
    });
  }
}
