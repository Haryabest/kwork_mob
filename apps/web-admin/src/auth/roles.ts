/** Роли внутренней панели (владелец сервиса / поддержка) */

export type StaffRole = 'admin' | 'support_agent';

export const STAFF_ROLE_LABELS: Record<StaffRole, string> = {
  admin: 'Владелец сервиса',
  support_agent: 'Специалист поддержки',
};

/** Маршруты, доступные каждой роли */
export const ROLE_ROUTES: Record<StaffRole, string[]> = {
  admin: [
    '/',
    '/ops',
    '/workers',
    '/users',
    '/users/:id',
    '/companies',
    '/companies/:id',
    '/invitations',
    '/promocodes',
    '/campaigns',
    '/analytics',
    '/push',
    '/moderation',
    '/soft-launch',
    '/maintenance',
    '/webhooks',
    '/tax',
    '/legal',
    '/settings',
    '/logs',
    '/user-events',
    '/alert-log',
    '/task-conflicts',
    '/access-log',
    '/storage',
    '/marketplace',
    '/watermark-verify',
    '/grafana',
    '/audit-export',
    '/b2b-api-usage',
    '/segmentation',
    '/support/tickets',
    '/support/tickets/:id',
    '/support/faq',
    '/support/stats',
  ],
  support_agent: [
    '/support/tickets',
    '/support/tickets/:id',
    '/support/faq',
    '/support/stats',
  ],
};

export function canAccess(role: StaffRole, path: string): boolean {
  return ROLE_ROUTES[role].some((pattern) => {
    if (pattern.includes(':')) {
      const re = new RegExp(`^${pattern.replace(/:[^/]+/g, '[^/]+')}$`);
      return re.test(path);
    }
    return pattern === path;
  });
}

export function defaultRouteFor(role: StaffRole): string {
  return role === 'support_agent' ? '/support/tickets' : '/';
}
