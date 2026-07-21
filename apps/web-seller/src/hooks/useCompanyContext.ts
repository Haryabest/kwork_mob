'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

export type CompanyCtx = { id: number; role: string };

export function useCompanyContext() {
  return useQuery({
    queryKey: ['company', 'mine'],
    queryFn: async () => {
      const { data } = await api.get<{ items: Array<{ id: number; role?: string }> }>('/company/mine');
      const first = data.items?.[0];
      if (!first?.id) return null;
      return { id: first.id, role: first.role || 'member' } satisfies CompanyCtx;
    },
    staleTime: 60_000,
  });
}
