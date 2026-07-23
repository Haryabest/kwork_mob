/** Бренд 3dvektor: синий → фиолетовый (Цвета и оформление 3dvektot.txt) */

import { createTheme, type MantineColorsTuple, type MantineTheme, type MantineThemeOverride } from '@mantine/core';

/** Глубокий синий #0057b8 как primary */
export const brand: MantineColorsTuple = [
  '#e6f1ff',
  '#cce3ff',
  '#99c7ff',
  '#66abff',
  '#338fff',
  '#0381E9',
  '#0057b8',
  '#004694',
  '#003570',
  '#00234c',
];

export const GRADIENT_PRIMARY = 'linear-gradient(135deg, #0057b8 0%, #0381E9 45%, #9403fd 100%)';
export const GRADIENT_SOFT = 'linear-gradient(135deg, rgba(0,87,184,0.12) 0%, rgba(148,3,253,0.10) 100%)';
export const PAGE_BG = '#f9fafb';
export const TEXT_MAIN = '#374151';
export const TEXT_MUTED = '#6d6c77';

export const brandTheme: MantineThemeOverride = createTheme({
  primaryColor: 'brand',
  primaryShade: 6,
  fontFamily: '"Open Sans", system-ui, -apple-system, Segoe UI, sans-serif',
  headings: { fontFamily: '"Open Sans", system-ui, sans-serif', fontWeight: '700' },
  defaultRadius: 'md',
  colors: { brand },
  black: TEXT_MAIN,
  other: {
    gradientPrimary: GRADIENT_PRIMARY,
    gradientSoft: GRADIENT_SOFT,
    pageBg: PAGE_BG,
    textMuted: TEXT_MUTED,
  },
  components: {
    Button: {
      defaultProps: { radius: 'md' },
      styles: (_theme: MantineTheme, params: { variant?: string }) => {
        if (params.variant === 'gradient' || params.variant === 'filled') {
          return {
            root: {
              backgroundImage: GRADIENT_PRIMARY,
              border: 0,
              color: '#fff',
              transition: 'transform 160ms ease, filter 160ms ease, box-shadow 160ms ease',
              '&:hover': {
                filter: 'brightness(1.06)',
                transform: 'translateY(-1px)',
                boxShadow: '0 8px 20px rgba(0, 87, 184, 0.28)',
              },
            },
          };
        }
        return {};
      },
    },
    Tabs: {
      defaultProps: { variant: 'pills', radius: 'xl' },
    },
    AppShell: {
      styles: {
        main: { background: 'transparent' },
        header: {
          background: 'rgba(255,255,255,0.92)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(0,87,184,0.08)',
        },
        navbar: {
          background: '#fff',
          borderRight: '1px solid rgba(0,87,184,0.08)',
        },
      },
    },
    Card: {
      defaultProps: { padding: 'lg', radius: 'lg', withBorder: false },
      styles: {
        root: {
          background: '#fff',
          boxShadow: '0 18px 40px rgba(0, 87, 184, 0.07)',
          border: '1px solid rgba(0, 87, 184, 0.06)',
        },
      },
    },
    SimpleGrid: {
      defaultProps: { spacing: 'xl' },
    },
  },
});
