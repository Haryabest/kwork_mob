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
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
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
import { ActionIcon, Avatar, Menu, UnstyledButton } from '@mantine/core';
import { auth } from '../lib/auth';
import { AuthGuard } from './AuthGuard';
import { api } from '../services/api';

const NAV = [
  { href: '/dashboard', label: 'Главная', icon: IconHome2 },
  { href: '/models', label: 'Модели', icon: IconBox },
  { href: '/orders', label: 'Заказы', icon: IconShoppingCart },
  { href: '/balance', label: 'Баланс', icon: IconCash },
  { href: '/team', label: 'Команда', icon: IconUsersGroup },
  { href: '/support', label: 'Поддержка', icon: IconHeadset },
  { href: '/settings', label: 'Настройки', icon: IconSettings },
] as const;

export function SellerShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [opened, { toggle }] = useDisclosure();

  return (
    <AuthGuard><AppShell
      header={{ height: 60 }}
      navbar={{ width: 240, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header px="md">
        <Group h="100%" justify="space-between">
          <Group>
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <ThemeIcon size="lg" radius="md" variant="light" color="brand">
              <IconStack2 size={18} />
            </ThemeIcon>
            <Box>
              <Text fw={700} size="sm" lh={1.2}>
                KWork Mob
              </Text>
              <Text size="xs" c="dimmed">
                Личный кабинет
              </Text>
            </Box>
          </Group>
          <Group gap="xs">
            <Badge component={Link} href="/balance" variant="light" color="brand" style={{ textDecoration: 'none' }}>
              Баланс: 0 ₽
            </Badge>
            <ActionIcon variant="subtle" aria-label="Уведомления"><IconBell size={19} /></ActionIcon>
            <Menu shadow="md" width={190}>
              <Menu.Target><UnstyledButton><Avatar color="brand" radius="xl">КМ</Avatar></UnstyledButton></Menu.Target>
              <Menu.Dropdown>
                <Menu.Label>Личный кабинет</Menu.Label>
                <Menu.Item component={Link} href="/settings">Настройки</Menu.Item>
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
          <Stack gap={4}>
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
                  onClick={() => {
                    if (opened) toggle();
                  }}
                />
              );
            })}
          </Stack>
        </AppShell.Section>
      </AppShell.Navbar>

      <AppShell.Main>{children}</AppShell.Main>
    </AppShell></AuthGuard>
  );
}
