'use client';

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { auth } from '../lib/auth';

/** LAN/dev: через Next proxy (/api/v1), иначе прямой URL из env. */
export function getApiUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl?.startsWith('/')) return envUrl;
  if (typeof window !== 'undefined') {
    const h = window.location.hostname;
    if (h !== 'localhost' && h !== '127.0.0.1') return '/api/v1';
  }
  return envUrl || 'http://localhost:8000/api/v1';
}

export const API_URL = getApiUrl();

/** WS на :8000 при прокси API через Next (/api/v1). */
export function wsBase(): string {
  const explicit = process.env.NEXT_PUBLIC_WS_URL;
  if (explicit) return explicit.replace(/\/$/, '');
  const http = getApiUrl().replace(/\/api\/v1\/?$/, '');
  if (!http || http.startsWith('/')) {
    if (typeof window !== 'undefined') {
      const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${wsProto}//${window.location.hostname}:8000`;
    }
    return 'ws://localhost:8000';
  }
  return http.replace(/^http/, 'ws');
}

export const api = axios.create({
  withCredentials: true,
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  config.baseURL = config.baseURL || getApiUrl();
  const token = auth.getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing: Promise<boolean> | null = null;

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const request = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
    if (error.response?.status !== 401 || !request || request._retry || request.url?.includes('/auth/refresh')) {
      return Promise.reject(error);
    }
    request._retry = true;
    refreshing ??= axios
      .post(`${getApiUrl()}/auth/refresh`, {}, { withCredentials: true })
      .then(() => true)
      .catch(() => {
        auth.clear();
        return false;
      })
      .finally(() => {
        refreshing = null;
      });
    const ok = await refreshing;
    if (!ok) return Promise.reject(error);
    return api(request);
  },
);

export function apiMessage(error: unknown, fallback = 'Не удалось выполнить запрос') {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data as
      | { detail?: string | { msg?: string; message?: string }[] | Record<string, unknown>; message?: string }
      | undefined;
    if (typeof detail?.detail === 'string') return detail.detail;
    if (typeof detail?.detail === 'object' && detail.detail !== null && !Array.isArray(detail.detail)) {
      const obj = detail.detail as { message?: string };
      if (obj.message) return obj.message;
    }
    if (Array.isArray(detail?.detail)) {
      return detail.detail.map((d) => (typeof d === 'string' ? d : d.msg)).filter(Boolean).join('; ') || fallback;
    }
    return detail?.message || fallback;
  }
  return fallback;
}
