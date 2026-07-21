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
  display_name?: string | null;
};
type CompanyMine = {
  id: number;
  name: string;
  balance?: number | null;
  role: string;
  is_owner?: boolean;
};

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const [meRes, ordersRes, modelsRes, companyRes] = await Promise.all([
        api.get<Me>('/user/me'),
        api.get<{ items: Order[] }>('/orders'),
        api.get<{ items: Model[] }>('/user/models', { params: { limit: 5 } }).catch(() => ({ data: { items: [] as Model[] } })),
        api.get<{ items: CompanyMine[] }>('/company/mine').catch(() => ({ data: { items: [] as CompanyMine[] } })),
      ]);
      const company = companyRes.data.items?.[0] ?? null;
      let teamCount: number | null = null;
      if (company?.is_owner || company?.role === 'owner') {
        try {
          const { data } = await api.get<{ total?: number; items?: unknown[] }>('/company/members', {
            params: { limit: 1, offset: 0 },
          });
          teamCount = data.total ?? data.items?.length ?? null;
        } catch {
          teamCount = null;
        }
      }
      const models = modelsRes.data.items ?? [];
      const thumbs = await Promise.all(
        models.slice(0, 5).map(async (m) => {
          try {
            const { data } = await api.get<{ thumbnail_url?: string }>(`/models/${m.uuid}/thumbnail`);
            return { uuid: m.uuid, url: data.thumbnail_url ?? null };
          } catch {
            return { uuid: m.uuid, url: null };
          }
        }),
      );
      const thumbByUuid = Object.fromEntries(thumbs.map((t) => [t.uuid, t.url]));
      return {
        me: meRes.data,
        orders: ordersRes.data.items ?? [],
        models,
        company,
        teamCount,
        thumbByUuid,
      };
    },
    staleTime: 30_000,
  });
}
