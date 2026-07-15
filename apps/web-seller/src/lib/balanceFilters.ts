const BALANCE_FILTERS_KEY = 'kwork_balance_filters_v1';

export type BalanceFiltersState = {
  authorId: string | null;
  dateFrom: string;
  dateTo: string;
  txType: string | null;
  pageSize: string | null;
};

export function loadBalanceFilters(): Partial<BalanceFiltersState> {
  if (typeof window === 'undefined') return {};
  try {
    const raw = localStorage.getItem(BALANCE_FILTERS_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as Partial<BalanceFiltersState>;
  } catch {
    return {};
  }
}

export function saveBalanceFilters(state: BalanceFiltersState): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(BALANCE_FILTERS_KEY, JSON.stringify(state));
  } catch {
    /* ignore quota */
  }
}

function filtersToState(filters: Record<string, unknown>): Partial<BalanceFiltersState> {
  return {
    authorId: filters.author_id != null ? String(filters.author_id) : null,
    dateFrom: String(filters.date_from || ''),
    dateTo: String(filters.date_to || ''),
    txType: String(filters.tx_type || 'all'),
    pageSize: String(filters.page_size || '20'),
  };
}

function stateToPayload(state: BalanceFiltersState, corporate: boolean): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    date_from: state.dateFrom,
    date_to: state.dateTo,
    tx_type: state.txType || 'all',
    page_size: Number(state.pageSize || 20),
  };
  if (corporate && state.authorId) {
    payload.author_id = Number(state.authorId);
  }
  return payload;
}

/** Server-side saved views §20.3.4 — fallback to localStorage. */
export async function loadBalanceFiltersSynced(
  apiGet: (path: string) => Promise<{ data: { filters?: Record<string, unknown> } }>,
  corporate: boolean,
): Promise<Partial<BalanceFiltersState>> {
  const path = corporate ? '/company/balance-filters' : '/user/balance-filters';
  try {
    const res = await apiGet(path);
    const mapped = filtersToState(res.data.filters || {});
    saveBalanceFilters({
      authorId: mapped.authorId ?? null,
      dateFrom: mapped.dateFrom || '',
      dateTo: mapped.dateTo || '',
      txType: mapped.txType || 'all',
      pageSize: mapped.pageSize || '20',
    });
    return mapped;
  } catch {
    return loadBalanceFilters();
  }
}

export async function saveBalanceFiltersSynced(
  apiPut: (path: string, body: Record<string, unknown>) => Promise<unknown>,
  corporate: boolean,
  state: BalanceFiltersState,
): Promise<void> {
  saveBalanceFilters(state);
  const path = corporate ? '/company/balance-filters' : '/user/balance-filters';
  try {
    await apiPut(path, stateToPayload(state, corporate));
  } catch {
    /* local fallback kept */
  }
}
