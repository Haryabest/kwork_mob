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
  UnstyledButton,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconBell,
  IconBuilding,
  IconChartBar,
  IconDiscount2,
  IconFileText,
  IconHelp,
  IconLogout,
  IconMessages,
  IconReceipt,
  IconScale,
  IconServer,
  IconSettings,
  IconShield,
  IconStack2,
  IconUsers,
  IconUserPlus,
} from '@tabler/icons-react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { STAFF_ROLE_LABELS, type StaffRole } from '../auth/roles';

const NAV: {
  path: string;
  label: string;
  roles: StaffRole[];
  icon: typeof IconChartBar;
}[] = [
  { path: '/', label: 'Дашборд', roles: ['admin'], icon: IconChartBar },
  { path: '/workers', label: 'Воркеры', roles: ['admin'], icon: IconServer },
  { path: '/users', label: 'Пользователи', roles: ['admin'], icon: IconUsers },
  { path: '/companies', label: 'B2B', roles: ['admin'], icon: IconBuilding },
  { path: '/invitations', label: 'Приглашения', roles: ['admin'], icon: IconUserPlus },
  { path: '/promocodes', label: 'Промокоды', roles: ['admin'], icon: IconDiscount2 },
  { path: '/campaigns', label: 'Кампании', roles: ['admin'], icon: IconStack2 },
  { path: '/push', label: 'Push', roles: ['admin'], icon: IconBell },
  { path: '/moderation', label: 'Модерация', roles: ['admin'], icon: IconShield },
  { path: '/tax', label: 'Налоги', roles: ['admin'], icon: IconReceipt },
  { path: '/legal', label: 'Юр. документы', roles: ['admin'], icon: IconScale },
  { path: '/settings', label: 'Настройки', roles: ['admin'], icon: IconSettings },
  { path: '/logs', label: 'Логи', roles: ['admin'], icon: IconFileText },
  { path: '/storage', label: 'Хранилище', roles: ['admin'], icon: IconServer },
  { path: '/support/tickets', label: 'Обращения', roles: ['admin', 'support_agent'], icon: IconMessages },
  { path: '/support/faq', label: 'FAQ', roles: ['admin', 'support_agent'], icon: IconHelp },
  { path: '/support/stats', label: 'Статистика поддержки', roles: ['admin', 'support_agent'], icon: IconChartBar },
];

function isActive(pathname: string, path: string): boolean {
  if (path === '/') return pathname === '/';
  return pathname === path || pathname.startsWith(`${path}/`);
}

export default function AppLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [opened, { toggle }] = useDisclosure();

  const items = NAV.filter((item) => user && item.roles.includes(user.role));

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{ width: 260, breakpoint: 'sm', collapsed: { mobile: !opened } }}
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
                KWork Staff
              </Text>
              <Text size="xs" c="dimmed">
                {user ? STAFF_ROLE_LABELS[user.role] : ''}
              </Text>
            </Box>
          </Group>
          <Group gap="xs">
            <Badge variant="light" color="brand">
              {user?.email}
            </Badge>
            <UnstyledButton onClick={logout}>
              <Group gap={6}>
                <IconLogout size={16} />
                <Text size="sm">Выйти</Text>
              </Group>
            </UnstyledButton>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        <AppShell.Section grow component={ScrollArea}>
          <Stack gap={4}>
            {items.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  label={item.label}
                  leftSection={<Icon size={18} stroke={1.5} />}
                  active={isActive(location.pathname, item.path)}
                  onClick={() => {
                    navigate(item.path);
                    if (opened) toggle();
                  }}
                />
              );
            })}
          </Stack>
        </AppShell.Section>
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
