'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

type Me = { balance: number; full_name?: string | null; account_type?: string | null };
type Order = { id: number; status: string; amount: number };
type Model = {
  uuid: string;
  order_id: number;
  glb_url?: string | null;
  publish_status?: string;
  created_at?: string;
};

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const [meRes, ordersRes, modelsRes] = await Promise.all([
        api.get<Me>('/user/me'),
        api.get<{ items: Order[] }>('/orders'),
        api.get<{ items: Model[] }>('/user/models').catch(() => ({ data: { items: [] as Model[] } })),
      ]);
      return {
        me: meRes.data,
        orders: ordersRes.data.items ?? [],
        models: modelsRes.data.items ?? [],
      };
    },
    staleTime: 30_000,
  });
}
