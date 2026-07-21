'use client';

import { Select } from '@mantine/core';
import { SUPPORTED_LOCALES, type Locale } from './types';
import { useI18n } from './I18nProvider';

const LABELS: Record<Locale, string> = {
  ru: 'Русский',
  en: 'English',
  kk: 'Қазақша',
  'zh-CN': '中文',
};

export function LanguageSelect({ label, description }: { label: string; description?: string }) {
  const { locale, setLocale } = useI18n();
  return (
    <Select
      label={label}
      description={description}
      value={locale}
      onChange={(v) => {
        if (v) void setLocale(v as Locale);
      }}
      data={SUPPORTED_LOCALES.map((l) => ({ value: l, label: LABELS[l] }))}
    />
  );
}
