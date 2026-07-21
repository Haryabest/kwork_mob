import { describe, expect, it } from 'vitest';
import { canAccess, defaultRouteFor, ROLE_ROUTES, STAFF_ROLE_LABELS } from './roles';

describe('canAccess', () => {
  const adminOnly = [
    '/',
    '/ops',
    '/workers',
    '/users',
    '/users/42',
    '/companies',
    '/companies/7',
    '/user-events',
    '/marketplace',
    '/grafana',
    '/watermark-verify',
    '/audit-export',
    '/b2b-api-usage',
    '/segmentation',
    '/storage',
    '/push',
    '/tax',
    '/legal',
  ];

  it.each(adminOnly)('admin может %s', (path) => {
    expect(canAccess('admin', path)).toBe(true);
  });

  it('support_agent не видит admin-разделы', () => {
    for (const path of adminOnly) {
      expect(canAccess('support_agent', path)).toBe(false);
    }
  });

  it('support_agent видит тикеты и FAQ', () => {
    expect(canAccess('support_agent', '/support/tickets')).toBe(true);
    expect(canAccess('support_agent', '/support/tickets/99')).toBe(true);
    expect(canAccess('support_agent', '/support/faq')).toBe(true);
    expect(canAccess('support_agent', '/support/stats')).toBe(true);
  });

  it('admin видит support-маршруты', () => {
    expect(canAccess('admin', '/support/tickets/1')).toBe(true);
  });

  it('не матчит похожие пути', () => {
    expect(canAccess('admin', '/users-extra')).toBe(false);
    expect(canAccess('admin', '/ops/extra')).toBe(false);
  });
});

describe('defaultRouteFor', () => {
  it('admin → дашборд', () => {
    expect(defaultRouteFor('admin')).toBe('/');
  });

  it('support → тикеты', () => {
    expect(defaultRouteFor('support_agent')).toBe('/support/tickets');
  });
});

describe('ROLE_ROUTES', () => {
  it('все admin-маршруты из nav покрыты ACL', () => {
    const navCritical = [
      '/ops',
      '/user-events',
      '/watermark-verify',
      '/grafana',
      '/audit-export',
      '/b2b-api-usage',
      '/segmentation',
    ];
    for (const path of navCritical) {
      expect(ROLE_ROUTES.admin).toContain(path);
    }
  });

  it('есть подписи ролей', () => {
    expect(STAFF_ROLE_LABELS.admin).toBeTruthy();
    expect(STAFF_ROLE_LABELS.support_agent).toBeTruthy();
  });
});
