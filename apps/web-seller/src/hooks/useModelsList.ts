'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

export type ModelsListParams = {
  companyId?: number;
  page: number;
  pageSize: number;
  search: string;
  publishFilter: string | null;
  category: string | null;
  tier: string | null;
  dateFrom: string;
  dateTo: string;
  authorId: string | null;
  sort: string | null;
  orderStatus: string | null;
};

type ModelsResponse = {
  items: unknown[];
  total: number;
  limit: number;
  offset: number;
};

export function useModelsList(params: ModelsListParams, enabled = true) {
  const {
    companyId,
    page,
    pageSize,
    search,
    publishFilter,
    category,
    tier,
    dateFrom,
    dateTo,
    authorId,
    sort,
    orderStatus,
  } = params;

  return useQuery({
    queryKey: [
      'models',
      companyId,
      page,
      pageSize,
      search,
      publishFilter,
      category,
      tier,
      dateFrom,
      dateTo,
      authorId,
      sort,
      orderStatus,
    ],
    enabled: enabled && companyId != null,
    queryFn: async () => {
      const q: Record<string, string | number> = {
        limit: pageSize,
        offset: (page - 1) * pageSize,
        sort: sort || 'newest',
        company_id: companyId as number,
      };
      if (search) q.search = search;
      if (dateFrom) q.date_from = dateFrom;
      if (dateTo) q.date_to = dateTo;
      if (tier) q.tier = tier;
      if (category) q.category = category;
      if (publishFilter) q.publish_filter = publishFilter;
      if (authorId) q.author_id = Number(authorId);
      if (orderStatus) q.order_status = orderStatus;
      const { data } = await api.get<ModelsResponse>('/user/models', { params: q });
      return data;
    },
    staleTime: 30_000,
  });
}
