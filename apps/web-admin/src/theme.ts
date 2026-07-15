/** Бренд 3dvektor: синий → фиолетовый */

import { createTheme, type MantineColorsTuple } from '@mantine/core';

const brand: MantineColorsTuple = [
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
export const PAGE_BG = '#f9fafb';

export const theme = createTheme({
  primaryColor: 'brand',
  primaryShade: 6,
  fontFamily: '"Open Sans", system-ui, -apple-system, Segoe UI, sans-serif',
  headings: { fontFamily: '"Open Sans", system-ui, sans-serif', fontWeight: '700' },
  defaultRadius: 'md',
  colors: { brand },
  black: '#374151',
  components: {
    Button: {
      defaultProps: { radius: 'md' },
      styles: (_theme: unknown, params: { variant?: string }) => {
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
      styles: {
        list: {
          gap: 8,
          flexWrap: 'wrap',
          borderBottom: 'none',
        },
        tab: {
          border: '1px solid rgba(0,87,184,0.14)',
          background: 'light-dark(#fff, var(--mantine-color-dark-6))',
          color: 'light-dark(#374151, var(--mantine-color-dark-0))',
          fontWeight: 600,
          transition: 'background 160ms ease, color 160ms ease, box-shadow 160ms ease',
          '&[data-active]': {
            backgroundImage: GRADIENT_PRIMARY,
            color: '#fff !important',
            borderColor: 'transparent',
            boxShadow: '0 8px 18px rgba(0, 87, 184, 0.28)',
          },
        },
      },
    },
    NavLink: {
      styles: {
        root: {
          borderRadius: 10,
          transition: 'background 160ms ease, color 160ms ease',
          '&[data-active]': {
            backgroundImage: GRADIENT_PRIMARY,
            color: '#fff',
            '& .mantine-NavLink-label': { color: '#fff', fontWeight: 600 },
            '& .mantine-NavLink-section': { color: '#fff' },
          },
        },
      },
    },
    AppShell: {
      styles: {
        main: { background: 'transparent' },
        header: {
          background: 'light-dark(rgba(255,255,255,0.92), rgba(20,21,23,0.92))',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(0,87,184,0.08)',
        },
        navbar: {
          background: 'light-dark(#fff, var(--mantine-color-dark-7))',
          borderRight: '1px solid rgba(0,87,184,0.08)',
        },
      },
    },
    Card: {
      defaultProps: { padding: 'lg', radius: 'lg', withBorder: false },
      styles: {
        root: {
          background: 'light-dark(#fff, var(--mantine-color-dark-6))',
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
