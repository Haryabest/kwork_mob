export type Locale = 'ru' | 'en' | 'kk' | 'zh-CN';

export type Messages = {
  nav: {
    dashboard: string;
    models: string;
    orders: string;
    balance: string;
    team: string;
    support: string;
    settings: string;
  };
  shell: {
    sellerCabinet: string;
    notifications: string;
    personalAccount: string;
    settings: string;
    logout: string;
  };
  settings: {
    title: string;
    description: string;
    profile: string;
    security: string;
    notifications: string;
    danger: string;
    language: string;
    languageHint: string;
    saveProfile: string;
    profileSaved: string;
    email: string;
    fullName: string;
    phone: string;
  };
  common: {
    langRu: string;
    langEn: string;
    langKk: string;
    langZh: string;
  };
};

export const LOCALE_COOKIE = 'kwork_locale';

export const SUPPORTED_LOCALES: Locale[] = ['ru', 'en', 'kk', 'zh-CN'];

export function normalizeLocale(code: string | null | undefined): Locale {
  if (!code) return 'ru';
  const raw = code.trim().toLowerCase().replace('_', '-');
  if (raw === 'zh' || raw === 'zh-cn' || raw === 'zh-hans') return 'zh-CN';
  if (raw.startsWith('en')) return 'en';
  if (raw.startsWith('kk')) return 'kk';
  if (raw === 'ru') return 'ru';
  if (SUPPORTED_LOCALES.includes(raw as Locale)) return raw as Locale;
  return 'ru';
}

export function detectBrowserLocale(): Locale {
  if (typeof navigator === 'undefined') return 'ru';
  return normalizeLocale(navigator.language);
}

export function localeToHtmlLang(locale: Locale): string {
  return locale === 'zh-CN' ? 'zh-Hans' : locale;
}

export function serverLocaleCode(locale: Locale): string {
  return locale === 'zh-CN' ? 'zh' : locale;
}
