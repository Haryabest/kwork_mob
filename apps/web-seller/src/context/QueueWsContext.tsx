'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { api, API_URL } from '../services/api';

export type QueueWsEvent = {
  order_id: number;
  status: string;
  at: string;
};

type QueueWsContextValue = {
  live: boolean;
  pendingCount: number;
  lastEvent: QueueWsEvent | null;
  clearPending: () => void;
};

const QueueWsContext = createContext<QueueWsContextValue>({
  live: false,
  pendingCount: 0,
  lastEvent: null,
  clearPending: () => undefined,
});

function wsBase(): string {
  const http = API_URL.replace(/\/api\/v1\/?$/, '');
  return http.replace(/^http/, 'ws');
}

export function QueueWsProvider({ children }: { children: ReactNode }) {
  const [live, setLive] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const [lastEvent, setLastEvent] = useState<QueueWsEvent | null>(null);
  const userIdRef = useRef<number | null>(null);

  const clearPending = useCallback(() => setPendingCount(0), []);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let closed = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    async function connect() {
      try {
        const me = await api.get<{ id: number }>('/user/me');
        userIdRef.current = me.data.id;
        const { data: wsAuth } = await api.get<{ access_token: string }>('/auth/ws-token');
        const token = wsAuth.access_token;
        if (!token || closed) return;
        const url = `${wsBase()}/ws/queue/${me.data.id}?token=${encodeURIComponent(token)}`;
        ws = new WebSocket(url);
        ws.onopen = () => setLive(true);
        ws.onclose = () => {
          setLive(false);
          if (!closed) {
            retryTimer = setTimeout(() => void connect(), 3000);
          }
        };
        ws.onerror = () => setLive(false);
        ws.onmessage = (ev) => {
          try {
            const msg = JSON.parse(ev.data as string) as {
              type?: string;
              order_id?: number;
              status?: string;
            };
            if (msg.type === 'order_status' && msg.order_id != null) {
              setLastEvent({
                order_id: Number(msg.order_id),
                status: msg.status || 'updated',
                at: new Date().toISOString(),
              });
              setPendingCount((n) => n + 1);
            }
          } catch {
            /* ignore */
          }
        };
      } catch {
        if (!closed) retryTimer = setTimeout(() => void connect(), 5000);
      }
    }

    void connect();
    return () => {
      closed = true;
      if (retryTimer) clearTimeout(retryTimer);
      ws?.close();
    };
  }, []);

  const value = useMemo(
    () => ({ live, pendingCount, lastEvent, clearPending }),
    [live, pendingCount, lastEvent, clearPending],
  );

  return <QueueWsContext.Provider value={value}>{children}</QueueWsContext.Provider>;
}

export function useQueueWs() {
  return useContext(QueueWsContext);
}
