'use client';

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { auth } from '../lib/auth';

export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = auth.getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing: Promise<string | null> | null = null;

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const request = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
    if (error.response?.status !== 401 || !request || request._retry || request.url?.includes('/auth/refresh')) {
      return Promise.reject(error);
    }
    request._retry = true;
    refreshing ??= axios
      .post<{ access_token: string; refresh_token?: string }>(`${API_URL}/auth/refresh`, {
        refresh_token: auth.getRefreshToken(),
      })
      .then(({ data }) => {
        auth.setTokens(data.access_token, data.refresh_token ?? auth.getRefreshToken() ?? '');
        return data.access_token;
      })
      .catch(() => {
        auth.clear();
        return null;
      })
      .finally(() => {
        refreshing = null;
      });
    const token = await refreshing;
    if (!token) return Promise.reject(error);
    request.headers.Authorization = `Bearer ${token}`;
    return api(request);
  },
);

export function apiMessage(error: unknown, fallback = 'Не удалось выполнить запрос') {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data as
      | { detail?: string | { msg?: string }[]; message?: string }
      | undefined;
    if (typeof detail?.detail === 'string') return detail.detail;
    if (Array.isArray(detail?.detail)) {
      return detail.detail.map((d) => (typeof d === 'string' ? d : d.msg)).filter(Boolean).join('; ') || fallback;
    }
    return detail?.message || fallback;
  }
  return fallback;
}
