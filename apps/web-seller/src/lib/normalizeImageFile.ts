const MAX_EDGE = 2048;
const MAX_EDGE_MOBILE = 1600;

function isMobileUa(): boolean {
  if (typeof navigator === 'undefined') return false;
  return /android|iphone|ipad|mobile/i.test(navigator.userAgent);
}

/** С телефона (HEIC/WebP/большие JPEG) → JPEG для стабильной загрузки в MinIO. */
export async function normalizeImageFile(file: File): Promise<File> {
  if (!file.type.startsWith('image/') && !/\.(jpe?g|png|webp|heic|heif)$/i.test(file.name)) {
    return file;
  }
  const maxEdge = isMobileUa() ? MAX_EDGE_MOBILE : MAX_EDGE;
  if (file.type === 'image/jpeg' && file.size < 4 * 1024 * 1024) {
    return file;
  }
  try {
    const bitmap = await createImageBitmap(file);
    let width = bitmap.width;
    let height = bitmap.height;
    const maxSide = Math.max(width, height);
    if (maxSide > maxEdge) {
      const scale = maxEdge / maxSide;
      width = Math.round(width * scale);
      height = Math.round(height * scale);
    }
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      bitmap.close?.();
      return file;
    }
    ctx.drawImage(bitmap, 0, 0, width, height);
    bitmap.close?.();
    const blob = await new Promise<Blob | null>((resolve) => {
      canvas.toBlob(resolve, 'image/jpeg', isMobileUa() ? 0.82 : 0.9);
    });
    if (!blob) return file;
    const base = file.name.replace(/\.[^.]+$/, '') || 'photo';
    return new File([blob], `${base}.jpg`, { type: 'image/jpeg', lastModified: Date.now() });
  } catch {
    return file;
  }
}

export async function normalizeImageFiles(files: (File | null)[]): Promise<File[]> {
  const out: File[] = [];
  for (const f of files) {
    if (!f) continue;
    out.push(await normalizeImageFile(f));
  }
  return out;
}
