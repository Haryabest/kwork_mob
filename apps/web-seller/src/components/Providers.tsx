'use client';

import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';
import { brandTheme } from '../theme/brand';
import { I18nProvider } from '../i18n/I18nProvider';

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: 1 } } }));

  return (
    <QueryClientProvider client={queryClient}>
      <MantineProvider theme={brandTheme} defaultColorScheme="light">
        <I18nProvider>
          <Notifications position="top-right" />
          {children}
        </I18nProvider>
      </MantineProvider>
    </QueryClientProvider>
  );
}
