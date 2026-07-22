import { useEffect, useRef, useState } from 'react';

function wsBaseUrl(): string {
  const api = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';
  if (api.startsWith('/')) {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${window.location.host}`;
  }
  const origin = api.replace(/\/api\/v1\/?$/, '');
  return origin.replace(/^http/, 'ws');
}

/** WebSocket live refresh для admin dashboard §11.15. */
export function useAdminDashboardLive(onRefresh: () => void) {
  const [connected, setConnected] = useState(false);
  const onRefreshRef = useRef(onRefresh);
  onRefreshRef.current = onRefresh;

  useEffect(() => {
    const token = localStorage.getItem('staff_access_token');
    if (!token) return;

    let ws: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;
    let closed = false;

    const connect = () => {
      if (closed) return;
      const url = `${wsBaseUrl()}/ws/admin/dashboard?token=${encodeURIComponent(token)}`;
      ws = new WebSocket(url);
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        if (!closed) retry = setTimeout(connect, 5000);
      };
      ws.onerror = () => ws?.close();
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data as string) as { type?: string };
          if (msg.type === 'dashboard_refresh' || msg.type === 'order_status') {
            onRefreshRef.current();
          }
        } catch {
          /* ignore */
        }
      };
    };

    connect();
    const ping = window.setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping' }));
    }, 30000);

    return () => {
      closed = true;
      window.clearInterval(ping);
      if (retry) clearTimeout(retry);
      ws?.close();
    };
  }, []);

  return connected;
}
