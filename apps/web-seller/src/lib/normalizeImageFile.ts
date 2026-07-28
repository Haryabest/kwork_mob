const MAX_EDGE = 4096;

/** С телефона (HEIC/WebP/большие JPEG) → JPEG для стабильной загрузки в MinIO. */
export async function normalizeImageFile(file: File): Promise<File> {
  if (!file.type.startsWith('image/') && !/\.(jpe?g|png|webp|heic|heif)$/i.test(file.name)) {
    return file;
  }
  if (file.type === 'image/jpeg' && file.size < 8 * 1024 * 1024) {
    return file;
  }
  try {
    const bitmap = await createImageBitmap(file);
    let width = bitmap.width;
    let height = bitmap.height;
    const maxSide = Math.max(width, height);
    if (maxSide > MAX_EDGE) {
      const scale = MAX_EDGE / maxSide;
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
      canvas.toBlob(resolve, 'image/jpeg', 0.9);
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
