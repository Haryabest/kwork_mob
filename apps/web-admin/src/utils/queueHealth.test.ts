import { describe, expect, it } from 'vitest';
import { isPgQueueSynced } from './queueHealth';

describe('isPgQueueSynced', () => {
  it('совпадение — актуальна', () => {
    expect(isPgQueueSynced(5, { normal: 3, high: 2 })).toBe(true);
  });

  it('расхождение', () => {
    expect(isPgQueueSynced(5, { normal: 3, high: 1 })).toBe(false);
  });

  it('пустая очередь', () => {
    expect(isPgQueueSynced(0, { normal: 0, high: 0 })).toBe(true);
  });
});
