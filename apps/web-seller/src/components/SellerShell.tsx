'use client';

import {
  AppShell,
  Badge,
  Box,
  Burger,
  Group,
  NavLink,
  ScrollArea,
  Stack,
  Text,
  ThemeIcon,
  ActionIcon,
  Avatar,
  Indicator,
  Menu,
  UnstyledButton,
  useMantineColorScheme,
} from '@mantine/core';
import { useDisclosure, useMediaQuery } from '@mantine/hooks';
import {
  IconBox,
  IconCash,
  IconBell,
  IconHome2,
  IconHeadset,
  IconLogout,
  IconSettings,
  IconShoppingCart,
  IconStack2,
  IconUsersGroup,
  IconDeviceDesktop,
  IconMoon,
  IconSun,
} from '@tabler/icons-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { AuthGuard } from './AuthGuard';
import { api } from '../services/api';
import { GRADIENT_PRIMARY } from '../theme/brand';
import { useT } from '../i18n/I18nProvider';
import { useCompanyContext } from '../hooks/useCompanyContext';
import { QueueWsProvider, useQueueWs } from '../context/QueueWsContext';

const NAV_KEYS = [
  { href: '/dashboard', key: 'dashboard' as const, icon: IconHome2 },
  { href: '/models', key: 'models' as const, icon: IconBox },
  { href: '/orders', key: 'orders' as const, icon: IconShoppingCart },
  { href: '/balance', key: 'balance' as const, icon: IconCash },
  { href: '/team', key: 'team' as const, icon: IconUsersGroup },
  { href: '/support', key: 'support' as const, icon: IconHeadset },
  { href: '/settings', key: 'settings' as const, icon: IconSettings },
] as const;

export function SellerShell({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <QueueWsProvider>
        <SellerShellInner>{children}</SellerShellInner>
      </QueueWsProvider>
    </AuthGuard>
  );
}

function SellerShellInner({ children }: { children: ReactNode }) {
  const t = useT();
  const pathname = usePathname();
  const router = useRouter();
  const [opened, { toggle, close }] = useDisclosure();
  const [balance, setBalance] = useState<number | null>(null);
  const [unread, setUnread] = useState(0);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [userLabel, setUserLabel] = useState('3D');
  const isMobile = useMediaQuery('(max-width: 767px)');
  const { live: queueLive, pendingCount: queuePending, clearPending } = useQueueWs();
  const { colorScheme, setColorScheme } = useMantineColorScheme();
  const cycleTheme = () => {
    const next = colorScheme === 'auto' ? 'light' : colorScheme === 'light' ? 'dark' : 'auto';
    setColorScheme(next);
  };
  const themeLabel =
    colorScheme === 'auto' ? 'Системная тема' : colorScheme === 'dark' ? 'Светлая тема' : 'Тёмная тема';
  const { data: companyCtx } = useCompanyContext();
  const isOwner = companyCtx?.role === 'owner';

  const navItems = NAV_KEYS.filter((item) => item.key !== 'team' || isOwner);

  useEffect(() => {
    api
      .get<{ balance: number; avatar_url?: string | null; full_name?: string | null; email?: string }>('/user/me')
      .then(({ data }) => {
        setBalance(data.balance ?? 0);
        setAvatarUrl(data.avatar_url || null);
        const label = (data.full_name || data.email || '3D').slice(0, 2).toUpperCase();
        setUserLabel(label);
      })
      .catch(() => setBalance(null));
    api
      .get<{ unread?: number }>('/user/notifications', { params: { limit: 1, offset: 0 } })
      .then(({ data }) => setUnread(data.unread ?? 0))
      .catch(() => setUnread(0));
  }, [pathname]);

  return (
    <AppShell
        header={{ height: isMobile ? 56 : 64 }}
        navbar={{ width: 248, breakpoint: 'sm', collapsed: { mobile: !opened } }}
        padding={0}
      >
        <AppShell.Header px={{ base: 'sm', sm: 'md' }}>
          <Group h="100%" justify="space-between" wrap="nowrap">
            <Group wrap="nowrap" gap="sm">
              <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
              <ThemeIcon size={isMobile ? 'md' : 'lg'} radius="md" style={{ backgroundImage: GRADIENT_PRIMARY }}>
                <IconStack2 size={18} color="#fff" />
              </ThemeIcon>
              <Box>
                <Text fw={700} size="sm" lh={1.15}>
                  3dvektor
                </Text>
                <Text size="xs" c="#6d6c77" visibleFrom="xs">
                  {t.shell.sellerCabinet}
                </Text>
              </Box>
            </Group>
            <Group gap={6} wrap="nowrap">
              <ActionIcon
                variant="subtle"
                aria-label={themeLabel}
                onClick={cycleTheme}
                visibleFrom="sm"
              >
                {colorScheme === 'auto' ? (
                  <IconDeviceDesktop size={19} />
                ) : colorScheme === 'dark' ? (
                  <IconSun size={19} />
                ) : (
                  <IconMoon size={19} />
                )}
              </ActionIcon>
              <Badge
                component={Link}
                href="/balance"
                variant="light"
                color="brand"
                style={{ textDecoration: 'none' }}
                size={isMobile ? 'sm' : 'md'}
              >
                {balance == null ? '…' : `${balance.toLocaleString('ru-RU')} ₽`}
              </Badge>
              <Indicator
                inline
                disabled={unread === 0}
                label={unread > 99 ? '99+' : unread}
                size={18}
                color="red"
              >
                <ActionIcon
                  component={Link}
                  href="/notifications"
                  variant="subtle"
                  aria-label={t.shell.notifications}
                  size="lg"
                  visibleFrom="sm"
                >
                  <IconBell size={19} />
                </ActionIcon>
              </Indicator>
              <Menu shadow="md" width={190}>
                <Menu.Target>
                  <UnstyledButton style={{ minHeight: 44 }}>
                    <Avatar src={avatarUrl || undefined} radius="xl" style={{ backgroundImage: avatarUrl ? undefined : GRADIENT_PRIMARY, color: '#fff' }}>
                      {userLabel}
                    </Avatar>
                  </UnstyledButton>
                </Menu.Target>
                <Menu.Dropdown>
                  <Menu.Label>{t.shell.personalAccount}</Menu.Label>
                  <Menu.Item component={Link} href="/settings">
                    {t.shell.settings}
                  </Menu.Item>
                  <Menu.Divider />
                  <Menu.Item
                    color="red"
                    leftSection={<IconLogout size={16} />}
                    onClick={async () => {
                      try {
                        await api.post('/auth/logout', {});
                      } catch {
                        /* ignore */
                      }
                      router.replace('/');
                    }}
                  >
                    {t.shell.logout}
                  </Menu.Item>
                </Menu.Dropdown>
              </Menu>
            </Group>
          </Group>
        </AppShell.Header>

        <AppShell.Navbar p="md">
          <AppShell.Section grow component={ScrollArea}>
            <Stack gap={8}>
              {navItems.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                const showQueueDot = item.key === 'orders' && queuePending > 0;
                return (
                  <NavLink
                    key={item.href}
                    component={Link}
                    href={item.href}
                    label={t.nav[item.key]}
                    leftSection={<Icon size={18} stroke={1.5} />}
                    rightSection={
                      showQueueDot ? (
                        <Badge size="xs" color="teal" circle>
                          {queuePending > 99 ? '99+' : queuePending}
                        </Badge>
                      ) : item.key === 'orders' && queueLive ? (
                        <Badge size="xs" color="green" variant="dot" />
                      ) : null
                    }
                    active={active}
                    onClick={() => {
                      if (item.key === 'orders') clearPending();
                      close();
                    }}
                  />
                );
              })}
              <NavLink
                component={Link}
                href="/notifications"
                label={t.shell.notifications}
                leftSection={<IconBell size={18} stroke={1.5} />}
                rightSection={
                  unread > 0 ? (
                    <Badge size="xs" color="red" circle>
                      {unread > 99 ? '99+' : unread}
                    </Badge>
                  ) : null
                }
                active={pathname === '/notifications'}
                onClick={() => close()}
                hiddenFrom="sm"
              />
            </Stack>
          </AppShell.Section>
        </AppShell.Navbar>

        <AppShell.Main className="vz-canvas">
          <Box p={{ base: 'sm', sm: 'md', lg: 'lg' }} className="vz-page" style={{ width: '100%', maxWidth: 'none' }}>
            {children}
          </Box>
        </AppShell.Main>
    </AppShell>
  );
}
