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
  Menu,
  UnstyledButton,
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
} from '@tabler/icons-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { auth } from '../lib/auth';
import { AuthGuard } from './AuthGuard';
import { api } from '../services/api';
import { GRADIENT_PRIMARY } from '../theme/brand';

const NAV = [
  { href: '/dashboard', label: 'Главная', icon: IconHome2 },
  { href: '/models', label: 'Мои модели', icon: IconBox },
  { href: '/orders', label: 'Заказы', icon: IconShoppingCart },
  { href: '/balance', label: 'Баланс', icon: IconCash },
  { href: '/team', label: 'Команда', icon: IconUsersGroup },
  { href: '/support', label: 'Поддержка', icon: IconHeadset },
  { href: '/settings', label: 'Настройки', icon: IconSettings },
] as const;

export function SellerShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [opened, { toggle, close }] = useDisclosure();
  const [balance, setBalance] = useState<number | null>(null);
  const isMobile = useMediaQuery('(max-width: 767px)');

  useEffect(() => {
    api
      .get<{ balance: number }>('/user/me')
      .then(({ data }) => setBalance(data.balance ?? 0))
      .catch(() => setBalance(null));
  }, [pathname]);

  return (
    <AuthGuard>
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
                  Кабинет селлера
                </Text>
              </Box>
            </Group>
            <Group gap={6} wrap="nowrap">
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
              <ActionIcon variant="subtle" aria-label="Уведомления" size="lg" visibleFrom="sm">
                <IconBell size={19} />
              </ActionIcon>
              <Menu shadow="md" width={190}>
                <Menu.Target>
                  <UnstyledButton style={{ minHeight: 44 }}>
                    <Avatar radius="xl" style={{ backgroundImage: GRADIENT_PRIMARY, color: '#fff' }}>
                      3D
                    </Avatar>
                  </UnstyledButton>
                </Menu.Target>
                <Menu.Dropdown>
                  <Menu.Label>Личный кабинет</Menu.Label>
                  <Menu.Item component={Link} href="/settings">
                    Настройки
                  </Menu.Item>
                  <Menu.Divider />
                  <Menu.Item
                    color="red"
                    leftSection={<IconLogout size={16} />}
                    onClick={async () => {
                      const refresh = auth.getRefreshToken();
                      try {
                        if (refresh) await api.post('/auth/logout', { refresh_token: refresh });
                      } catch {
                        /* ignore */
                      }
                      auth.clear();
                      router.replace('/');
                    }}
                  >
                    Выйти
                  </Menu.Item>
                </Menu.Dropdown>
              </Menu>
            </Group>
          </Group>
        </AppShell.Header>

        <AppShell.Navbar p="md">
          <AppShell.Section grow component={ScrollArea}>
            <Stack gap={8}>
              {NAV.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                return (
                  <NavLink
                    key={item.href}
                    component={Link}
                    href={item.href}
                    label={item.label}
                    leftSection={<Icon size={18} stroke={1.5} />}
                    active={active}
                    onClick={() => close()}
                  />
                );
              })}
            </Stack>
          </AppShell.Section>
        </AppShell.Navbar>

        <AppShell.Main className="vz-canvas">
          <Box p={{ base: 'sm', sm: 'md', lg: 'lg' }} className="vz-page" style={{ width: '100%', maxWidth: 'none' }}>
            {children}
          </Box>
        </AppShell.Main>
      </AppShell>
    </AuthGuard>
  );
}
