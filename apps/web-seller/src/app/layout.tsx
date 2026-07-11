import type { Metadata } from 'next';
import { ColorSchemeScript } from '@mantine/core';
import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
import { Providers } from '../components/Providers';

export const metadata: Metadata = {
  title: 'KWork Mob — Личный кабинет',
  robots: {
    index: false,
    follow: false,
    noarchive: true,
    nosnippet: true,
    googleBot: { index: false, follow: false, noarchive: true, nosnippet: true },
  },
  other: {
    robots: 'noindex, nofollow, noarchive, nosnippet',
    googlebot: 'noindex, nofollow, noarchive, nosnippet',
    yandex: 'noindex, nofollow, noarchive, nosnippet',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <head>
        <ColorSchemeScript defaultColorScheme="light" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
