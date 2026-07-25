import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const TOKEN_KEY = 'staff_access_token';
const REFRESH_KEY = 'staff_refresh_token';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing: Promise<boolean> | null = null;

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const request = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
    if (
      error.response?.status !== 401 ||
      !request ||
      request._retry ||
      request.url?.includes('/auth/refresh')
    ) {
      return Promise.reject(error);
    }
    const refresh = localStorage.getItem(REFRESH_KEY);
    if (!refresh) return Promise.reject(error);
    request._retry = true;
    refreshing ??= api
      .post<{ access_token: string; refresh_token: string }>('/auth/refresh', {
        refresh_token: refresh,
      })
      .then(({ data }) => {
        authStorage.save(data.access_token, data.refresh_token);
        return true;
      })
      .catch(() => {
        authStorage.clear();
        return false;
      })
      .finally(() => {
        refreshing = null;
      });
    const ok = await refreshing;
    if (!ok) return Promise.reject(error);
    const nextToken = localStorage.getItem(TOKEN_KEY);
    if (nextToken) request.headers.Authorization = `Bearer ${nextToken}`;
    return api(request);
  },
);

export const authStorage = {
  clear() {
    localStorage.removeItem('staff_access_token');
    localStorage.removeItem('staff_refresh_token');
    localStorage.removeItem('staff_user');
    localStorage.removeItem('staff_last_activity');
  },
  save(access: string, refresh?: string) {
    localStorage.setItem('staff_access_token', access);
    if (refresh) localStorage.setItem('staff_refresh_token', refresh);
  },
};

export function getApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((d) => (typeof d === 'string' ? d : d.msg)).join(', ');
    }
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return 'Ошибка запроса';
}
