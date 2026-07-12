'use client';

import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import type { ReactNode } from 'react';
import { brandTheme } from '../theme/brand';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <MantineProvider theme={brandTheme} defaultColorScheme="light">
      <Notifications position="top-right" />
      {children}
    </MantineProvider>
  );
}
