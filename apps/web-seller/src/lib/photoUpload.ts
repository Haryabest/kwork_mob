import axios from 'axios';

export type PhotoUploadPhase = 'prepare' | 'upload' | 'create';

export function isNetworkishError(error: unknown): boolean {
  if (!axios.isAxiosError(error)) return false;
  if (!error.response) return true;
  const status = error.response.status;
  return status === 408 || status === 429 || status >= 500;
}

function detailText(error: unknown): string {
  if (!axios.isAxiosError(error)) return '';
  const detail = error.response?.data as { detail?: unknown } | undefined;
  if (typeof detail?.detail === 'string') return detail.detail;
  return '';
}

export function photoUploadErrorMessage(error: unknown, phase: PhotoUploadPhase): string {
  const detail = detailText(error);
  const network = isNetworkishError(error);

  if (phase === 'prepare') {
    if (network) {
      return 'Не удалось подготовить загрузку: проблема с сетью или сервером. Проверьте интернет и попробуйте снова.';
    }
    return detail || 'Не удалось подготовить загрузку фото. Обновите страницу и попробуйте ещё раз.';
  }

  if (phase === 'upload' || /не хватает фото|загрузите фото/i.test(detail)) {
    if (network || !error || (axios.isAxiosError(error) && !error.response)) {
      return 'Загрузка фото прервалась (сеть или таймаут). Выберите снимки заново и нажмите «Создать заказ» ещё раз.';
    }
    if (detail) {
      return `${detail} Загрузите фото заново и повторите.`;
    }
    return 'Не все фото загрузились на сервер. Выберите снимки заново и повторите отправку.';
  }

  return detail || 'Не удалось создать заказ. Проверьте фото и попробуйте снова.';
}

export function shouldResetPhotoFiles(error: unknown, phase: PhotoUploadPhase): boolean {
  if (phase === 'upload') return true;
  if (phase === 'create') {
    const detail = detailText(error);
    return /не хватает фото|загрузите фото/i.test(detail);
  }
  return isNetworkishError(error) && phase === 'prepare';
}
