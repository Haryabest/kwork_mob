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
    '/workers',
    '/users',
    '/users/:id',
    '/companies',
    '/companies/:id',
    '/invitations',
    '/promocodes',
    '/campaigns',
    '/push',
    '/moderation',
    '/tax',
    '/legal',
    '/settings',
    '/logs',
    '/storage',
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
