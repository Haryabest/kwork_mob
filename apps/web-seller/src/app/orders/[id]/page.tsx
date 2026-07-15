'use client';

import {
  Alert,
  Badge,
  Button,
  Center,
  Group,
  Loader,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { IconCreditCard, IconX, IconWifi } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { useParams, useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';
import { SellerShell } from '../../../components/SellerShell';
import { PageHeader, Surface } from '../../../components/ui';
import { api, apiMessage, API_URL } from '../../../services/api';
import { auth } from '../../../lib/auth';

type OrderDetail = {
  id: number;
  task_uuid: string;
  category: string;
  tier: string;
  status: string;
  amount: number;
  created_at?: string;
  queue_position?: number | null;
  ewt_sec?: number | null;
  model?: { uuid: string; glb_url?: string } | null;
};

const STATUS_LABEL: Record<string, string> = {
  pending: 'Новый',
  awaiting_payment: 'Ожидает оплаты',
  queued: 'В очереди',
  processing: 'В обработке',
  completed: 'Готов',
  failed: 'Ошибка',
  cancelled: 'Отменён',
  blocked_nsfw: 'NSFW блок',
};

function wsBase(): string {
  const http = API_URL.replace(/\/api\/v1\/?$/, '');
  return http.replace(/^http/, 'ws');
}

export default function OrderDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [live, setLive] = useState(false);
  const [lastEvent, setLastEvent] = useState<string | null>(null);
  const userIdRef = useRef<number | null>(null);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get<OrderDetail>(`/orders/${id}`);
      setOrder(data);
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let closed = false;

    async function connect() {
      try {
        const me = await api.get<{ id: number }>('/user/me');
        userIdRef.current = me.data.id;
        const token = auth.getAccessToken();
        if (!token || closed) return;
        const url = `${wsBase()}/ws/queue/${me.data.id}?token=${encodeURIComponent(token)}`;
        ws = new WebSocket(url);
        ws.onopen = () => setLive(true);
        ws.onclose = () => {
          setLive(false);
          if (!closed) setTimeout(() => void connect(), 3000);
        };
        ws.onerror = () => setLive(false);
        ws.onmessage = (ev) => {
          try {
            const msg = JSON.parse(ev.data as string) as {
              type?: string;
              order_id?: number;
              status?: string;
              ewt_sec?: number;
              queue_position?: number;
              glb_url?: string;
              error?: string;
            };
            if (msg.type === 'order_status' && Number(msg.order_id) === Number(id)) {
              setLastEvent(`${msg.status} · ${new Date().toLocaleTimeString('ru-RU')}`);
              setOrder((prev) =>
                prev
                  ? {
                      ...prev,
                      status: msg.status || prev.status,
                      ewt_sec: msg.ewt_sec ?? prev.ewt_sec,
                      queue_position: msg.queue_position ?? prev.queue_position,
                      model: msg.glb_url
                        ? { uuid: prev.model?.uuid || '', glb_url: msg.glb_url }
                        : prev.model,
                    }
                  : prev,
              );
              if (msg.status === 'completed' || msg.status === 'failed') {
                void load();
              }
            }
          } catch {
            /* ignore */
          }
        };
      } catch {
        setLive(false);
      }
    }

    void connect();
    const poll = setInterval(() => void load(), 15000);
    return () => {
      closed = true;
      clearInterval(poll);
      ws?.close();
    };
  }, [id, load]);

  async function pay() {
    setBusy(true);
    try {
      const { data } = await api.post<{
        confirmation_url?: string;
        paid_from_balance?: boolean;
      }>(`/orders/${id}/pay`);
      if (data.confirmation_url) {
        window.location.href = data.confirmation_url;
        return;
      }
      notifications.show({
        color: 'teal',
        message: data.paid_from_balance ? 'Списано с баланса' : 'Ок',
      });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function cancel() {
    setBusy(true);
    try {
      await api.post(`/orders/${id}/cancel`);
      notifications.show({ message: 'Заказ отменён' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  if (loading || !order) {
    return (
      <SellerShell>
        <Center py="xl">
          <Loader color="brand" />
        </Center>
      </SellerShell>
    );
  }

  return (
    <SellerShell>
      <PageHeader
        title={`Заказ #${order.id}`}
        description={order.task_uuid}
        action={
          <Group gap="sm">
            <Badge
              variant="light"
              color={live ? 'teal' : 'gray'}
              leftSection={<IconWifi size={12} />}
            >
              {live ? 'Live WS' : 'WS…'}
            </Badge>
            <Badge size="lg" variant="light" color="brand">
              {STATUS_LABEL[order.status] || order.status}
            </Badge>
          </Group>
        }
      />

      {order.status === 'blocked_nsfw' && (
        <Alert color="red" title="NSFW блок" mb="md">
          Заказ заблокирован: обнаружен запрещённый контент на текстурах импорта. Средства возвращены
          на баланс компании. Аккаунт на ручной проверке до 24 ч (§10.8).
        </Alert>
      )}

      <div
        style={{
          display: 'grid',
          gap: '1.25rem',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        }}
      >
        {[
          ['Тариф', order.tier],
          ['Стоимость', `${order.amount.toLocaleString('ru-RU')} ₽`],
          ['Создан', order.created_at ? new Date(order.created_at).toLocaleString('ru-RU') : '—'],
        ].map(([label, value]) => (
          <Surface key={label}>
            <Text size="sm" c="#6d6c77">
              {label}
            </Text>
            <Text fw={700} size="lg" mt={8} className="vz-metric-value">
              {value}
            </Text>
          </Surface>
        ))}
      </div>

      <Surface>
        <Title order={4} mb="sm">
          Статус в реальном времени
        </Title>
        <Text size="sm" c="#6d6c77">
          Позиция в очереди: {order.queue_position ?? '—'} · EWT:{' '}
          {order.ewt_sec != null ? `${Math.round(order.ewt_sec / 60)} мин` : '—'}
        </Text>
        {lastEvent && (
          <Text size="sm" mt="sm" fw={600}>
            Последнее событие: {lastEvent}
          </Text>
        )}
        {order.model?.glb_url && (
          <Text size="sm" mt="sm">
            Модель: {order.model.glb_url}
          </Text>
        )}
        {order.model?.uuid && (
          <Button
            mt="md"
            variant="light"
            onClick={() => router.push(`/models/${order.model!.uuid}`)}
          >
            Открыть модель
          </Button>
        )}
      </Surface>

      <Group>
        {order.status === 'awaiting_payment' && (
          <Button leftSection={<IconCreditCard size={16} />} loading={busy} onClick={() => void pay()}>
            Оплатить (ЮKassa)
          </Button>
        )}
        {['pending', 'queued', 'awaiting_payment', 'paid'].includes(order.status) && (
          <Button color="red" variant="light" leftSection={<IconX size={16} />} loading={busy} onClick={() => void cancel()}>
            Отменить
          </Button>
        )}
        <Button variant="default" onClick={() => router.push('/orders')}>
          К списку
        </Button>
      </Group>
    </SellerShell>
  );
}
