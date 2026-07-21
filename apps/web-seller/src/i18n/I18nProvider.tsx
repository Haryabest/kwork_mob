'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api } from '../services/api';
import { getMessages } from './messages';
import {
  LOCALE_COOKIE,
  detectBrowserLocale,
  localeToHtmlLang,
  normalizeLocale,
  serverLocaleCode,
  type Locale,
  type Messages,
} from './types';

type I18nContextValue = {
  locale: Locale;
  messages: Messages;
  setLocale: (locale: Locale) => Promise<void>;
};

const I18nContext = createContext<I18nContextValue | null>(null);

function readStoredLocale(): Locale | null {
  if (typeof window === 'undefined') return null;
  const fromStorage = localStorage.getItem(LOCALE_COOKIE);
  if (fromStorage) return normalizeLocale(fromStorage);
  const match = document.cookie.match(new RegExp(`(?:^|; )${LOCALE_COOKIE}=([^;]+)`));
  if (match?.[1]) return normalizeLocale(decodeURIComponent(match[1]));
  return null;
}

function persistLocale(locale: Locale) {
  localStorage.setItem(LOCALE_COOKIE, locale);
  document.cookie = `${LOCALE_COOKIE}=${encodeURIComponent(locale)};path=/;max-age=31536000;SameSite=Lax`;
  document.documentElement.lang = localeToHtmlLang(locale);
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>('ru');
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const stored = readStoredLocale();
    const initial = stored ?? detectBrowserLocale();
    setLocaleState(initial);
    document.documentElement.lang = localeToHtmlLang(initial);
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    api
      .get<{ preferred_locale?: string }>('/user/me')
      .then(({ data }) => {
        if (data.preferred_locale) {
          const server = normalizeLocale(data.preferred_locale);
          setLocaleState(server);
          persistLocale(server);
        }
      })
      .catch(() => undefined);
  }, [ready]);

  const setLocale = useCallback(async (next: Locale) => {
    const loc = normalizeLocale(next);
    setLocaleState(loc);
    persistLocale(loc);
    try {
      await api.patch('/user/me', { preferred_locale: serverLocaleCode(loc) });
    } catch {
      /* guest or offline */
    }
  }, []);

  const value = useMemo<I18nContextValue>(
    () => ({
      locale,
      messages: getMessages(locale),
      setLocale,
    }),
    [locale, setLocale],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useI18n outside I18nProvider');
  return ctx;
}

export function useT() {
  return useI18n().messages;
}
