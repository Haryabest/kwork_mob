'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

export type OrderItem = {
  id: number;
  task_uuid: string;
  category: string;
  tier: string;
  status: string;
  amount: number;
  user_id?: number;
  created_at?: string;
};

const ACTIVE_STATUSES = new Set([
  'pending',
  'awaiting_payment',
  'paid',
  'queued',
  'processing',
]);

const LIVE_POLL_MS = 15_000;

export function useOrdersList(
  companyId?: number,
  authorId?: string | null,
  page = 1,
  pageSize = 20,
) {
  return useQuery({
    queryKey: ['orders', companyId, authorId, page, pageSize],
    enabled: companyId != null,
    queryFn: async () => {
      const params: Record<string, string | number> = {
        company_id: companyId as number,
        limit: pageSize,
        offset: (page - 1) * pageSize,
      };
      if (authorId) params.user_id = Number(authorId);
      const { data } = await api.get<{ items: OrderItem[]; total: number }>('/orders', { params });
      return { items: data.items ?? [], total: data.total ?? 0 };
    },
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? [];
      const hasActive = items.some((o) => ACTIVE_STATUSES.has(o.status));
      return hasActive ? LIVE_POLL_MS : false;
    },
  });
}

export function useCompanyMembers(enabled: boolean) {
  return useQuery({
    queryKey: ['company', 'members'],
    enabled,
    queryFn: async () => {
      const { data } = await api.get<{
        items: Array<{ user_id: number; email?: string | null; full_name?: string | null; role?: string }>;
      }>('/company/members');
      return data.items ?? [];
    },
    staleTime: 60_000,
  });
}
