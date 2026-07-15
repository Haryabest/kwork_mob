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
