import {
  ActionIcon,
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
  useMantineColorScheme,
} from '@mantine/core';
import { useDisclosure, useMediaQuery } from '@mantine/hooks';
import {
  IconBell,
  IconBuilding,
  IconChartBar,
  IconDiscount2,
  IconFileText,
  IconHelp,
  IconLogout,
  IconMessages,
  IconMoon,
  IconReceipt,
  IconScale,
  IconServer,
  IconSettings,
  IconShield,
  IconStack2,
  IconSun,
  IconUsers,
  IconUserPlus,
  IconRocket,
  IconTool,
  IconWebhook,
  IconUpload,
  IconHistory,
  IconShieldCheck,
  IconScan,
  IconActivity,
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
  { path: '/ops', label: 'Ops / DoD', roles: ['admin'], icon: IconActivity },
  { path: '/workers', label: 'Воркеры', roles: ['admin'], icon: IconServer },
  { path: '/soft-launch', label: 'Soft launch', roles: ['admin'], icon: IconRocket },
  { path: '/maintenance', label: 'Обслуживание', roles: ['admin'], icon: IconTool },
  { path: '/webhooks', label: 'B2B Webhooks', roles: ['admin'], icon: IconWebhook },
  { path: '/users', label: 'Пользователи', roles: ['admin'], icon: IconUsers },
  { path: '/companies', label: 'B2B', roles: ['admin'], icon: IconBuilding },
  { path: '/invitations', label: 'Приглашения', roles: ['admin'], icon: IconUserPlus },
  { path: '/marketplace', label: 'Marketplace API', roles: ['admin'], icon: IconUpload },
  { path: '/access-log', label: 'Access log', roles: ['admin'], icon: IconHistory },
  { path: '/task-conflicts', label: 'Task conflicts', roles: ['admin'], icon: IconShield },
  { path: '/watermark-verify', label: 'Watermark verify', roles: ['admin'], icon: IconShieldCheck },
  { path: '/grafana', label: 'Grafana', roles: ['admin'], icon: IconChartBar },
  { path: '/audit-export', label: 'Audit export', roles: ['admin'], icon: IconHistory },
  { path: '/b2b-api-usage', label: 'B2B API usage', roles: ['admin'], icon: IconBuilding },
  { path: '/segmentation', label: 'Сегментация', roles: ['admin'], icon: IconScan },
  { path: '/promocodes', label: 'Промокоды', roles: ['admin'], icon: IconDiscount2 },
  { path: '/campaigns', label: 'Кампании', roles: ['admin'], icon: IconStack2 },
  { path: '/analytics', label: 'Аналитика', roles: ['admin'], icon: IconChartBar },
  { path: '/push', label: 'Push', roles: ['admin'], icon: IconBell },
  { path: '/moderation', label: 'Модерация', roles: ['admin'], icon: IconShield },
  { path: '/tax', label: 'Налоги', roles: ['admin'], icon: IconReceipt },
  { path: '/legal', label: 'Юр. документы', roles: ['admin'], icon: IconScale },
  { path: '/settings', label: 'Настройки', roles: ['admin'], icon: IconSettings },
  { path: '/logs', label: 'Логи', roles: ['admin'], icon: IconFileText },
  { path: '/user-events', label: 'User events', roles: ['admin'], icon: IconHistory },
  { path: '/alert-log', label: 'Alert log', roles: ['admin'], icon: IconBell },
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
  const { user, logout, vpnStatus } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [opened, { toggle, close }] = useDisclosure();
  const isMobile = useMediaQuery('(max-width: 767px)');
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();

  const items = NAV.filter((item) => user && item.roles.includes(user.role));

  return (
    <AppShell
      header={{ height: isMobile ? 56 : 64 }}
      navbar={{
        width: 268,
        breakpoint: 'sm',
        collapsed: { mobile: !opened },
      }}
      padding={0}
    >
      <AppShell.Header px={{ base: 'sm', sm: 'md' }}>
        <Group h="100%" justify="space-between" wrap="nowrap">
          <Group wrap="nowrap" gap="sm">
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <ThemeIcon
              size={isMobile ? 'md' : 'lg'}
              radius="md"
              style={{
                backgroundImage: 'linear-gradient(135deg, #0057b8 0%, #0381E9 45%, #9403fd 100%)',
              }}
            >
              <IconStack2 size={18} color="#fff" />
            </ThemeIcon>
            <Box>
              <Text fw={700} size="sm" lh={1.15}>
                3dvektor
              </Text>
              <Text size="xs" c="#6d6c77" visibleFrom="xs">
                {user ? STAFF_ROLE_LABELS[user.role] : 'Staff'}
              </Text>
            </Box>
          </Group>
          <Group gap="xs" wrap="nowrap">
            {vpnStatus && (
              <Badge
                variant="light"
                color={vpnStatus.vpn_required && !vpnStatus.vpn_ok ? 'red' : 'teal'}
                title={vpnStatus.ip ? `IP: ${vpnStatus.ip}` : undefined}
              >
                VPN {vpnStatus.vpn_ok || !vpnStatus.vpn_required ? 'OK' : '—'}
              </Badge>
            )}
            <Badge variant="light" color="brand" visibleFrom="sm" maw={180} style={{ overflow: 'hidden' }}>
              {user?.email}
            </Badge>
            <ActionIcon
              variant="light"
              color="brand"
              onClick={toggleColorScheme}
              aria-label="Тема"
              title={colorScheme === 'dark' ? 'Светлая тема' : 'Тёмная тема'}
            >
              {colorScheme === 'dark' ? <IconSun size={18} /> : <IconMoon size={18} />}
            </ActionIcon>
            <UnstyledButton onClick={logout} style={{ minHeight: 44, paddingInline: 8 }}>
              <Group gap={6} wrap="nowrap">
                <IconLogout size={18} />
                <Text size="sm" visibleFrom="sm">
                  Выйти
                </Text>
              </Group>
            </UnstyledButton>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        <AppShell.Section grow component={ScrollArea}>
          <Stack gap={8}>
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
                    close();
                  }}
                />
              );
            })}
          </Stack>
        </AppShell.Section>
      </AppShell.Navbar>

      <AppShell.Main className="vz-canvas">
        <Box p={{ base: 'sm', sm: 'md', lg: 'lg' }} style={{ width: '100%' }}>
          <Outlet />
        </Box>
      </AppShell.Main>
    </AppShell>
  );
}
