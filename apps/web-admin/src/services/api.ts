import axios from 'axios';

const TOKEN_KEY = 'staff_access_token';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

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
