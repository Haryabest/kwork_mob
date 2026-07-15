import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  loadBalanceFilters,
  loadBalanceFiltersSynced,
  saveBalanceFilters,
} from './balanceFilters';

describe('balanceFilters (localStorage)', () => {
  beforeEach(() => localStorage.clear());

  it('сохраняет и читает фильтры', () => {
    saveBalanceFilters({
      authorId: '42',
      dateFrom: '2026-01-01',
      dateTo: '2026-02-01',
      txType: 'topup',
      pageSize: '50',
    });
    expect(loadBalanceFilters()).toEqual({
      authorId: '42',
      dateFrom: '2026-01-01',
      dateTo: '2026-02-01',
      txType: 'topup',
      pageSize: '50',
    });
  });

  it('возвращает {} без сохранённых данных', () => {
    expect(loadBalanceFilters()).toEqual({});
  });
});

describe('loadBalanceFiltersSynced', () => {
  beforeEach(() => localStorage.clear());

  it('маппит серверные фильтры компании', async () => {
    const apiGet = vi.fn().mockResolvedValue({
      data: { filters: { author_id: 7, date_from: '2026-03-01', tx_type: 'debit', page_size: 20 } },
    });
    const mapped = await loadBalanceFiltersSynced(apiGet, true);
    expect(apiGet).toHaveBeenCalledWith('/company/balance-filters');
    expect(mapped.authorId).toBe('7');
    expect(mapped.txType).toBe('debit');
  });

  it('фолбэк на localStorage при ошибке сети', async () => {
    saveBalanceFilters({
      authorId: null,
      dateFrom: '2026-01-01',
      dateTo: '',
      txType: 'all',
      pageSize: '20',
    });
    const apiGet = vi.fn().mockRejectedValue(new Error('network'));
    const mapped = await loadBalanceFiltersSynced(apiGet, false);
    expect(mapped.dateFrom).toBe('2026-01-01');
  });
});
