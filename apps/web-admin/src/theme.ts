import { createTheme, MantineColorsTuple } from '@mantine/core';

/** Акцент: глубокий teal (не pink/grape) */
const brand: MantineColorsTuple = [
  '#e8f7f6',
  '#d0efed',
  '#a3ddd9',
  '#6fc8c2',
  '#3fb0a8',
  '#1f9a91',
  '#0B7A73',
  '#09635e',
  '#074e4a',
  '#053a37',
];

export const theme = createTheme({
  primaryColor: 'brand',
  fontFamily: 'Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif',
  defaultRadius: 'md',
  colors: { brand },
});
