import { describe, expect, it } from 'vitest';
import { detectBrowserLocale, normalizeLocale } from './types';

describe('i18n locale', () => {
  it('normalizes zh variants', () => {
    expect(normalizeLocale('zh')).toBe('zh-CN');
    expect(normalizeLocale('zh-CN')).toBe('zh-CN');
  });

  it('falls back to ru', () => {
    expect(normalizeLocale('fr')).toBe('ru');
  });

  it('detectBrowserLocale returns supported locale', () => {
    const loc = detectBrowserLocale();
    expect(['ru', 'en', 'kk', 'zh-CN']).toContain(loc);
  });
});
