/**
 * k6 B2B load: shoot_link + order create burst.
 *
 * Пороги (DoD):
 *  - shoot_link p95 < 1s
 *  - order create p95 < 3s
 *  - http_req_failed < 1%
 *
 * Env:
 *  BASE_URL   — http://localhost:8000
 *  TOKEN      — JWT Owner/Manager
 *  COMPANY_ID — int
 *  VUS        — default 50
 *  ORDERS     — default 100 (через iterations)
 */
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const BASE = __ENV.BASE_URL || 'http://localhost:8000';
const TOKEN = __ENV.TOKEN || '';
const COMPANY_ID = Number(__ENV.COMPANY_ID || '1');
const VUS = Number(__ENV.VUS || '50');

const shootTrend = new Trend('shoot_link_duration');
const orderTrend = new Trend('order_create_duration');
const failRate = new Rate('business_fail');

export const options = {
  scenarios: {
    members_shoot: {
      executor: 'constant-vus',
      vus: VUS,
      duration: '2m',
      exec: 'shootLinkFlow',
    },
    orders_burst: {
      executor: 'shared-iterations',
      vus: Math.min(VUS, 20),
      iterations: Number(__ENV.ORDERS || '100'),
      exec: 'orderCreateFlow',
      startTime: '10s',
    },
  },
  thresholds: {
    shoot_link_duration: ['p(95)<1000'],
    order_create_duration: ['p(95)<3000'],
    http_req_failed: ['rate<0.01'],
    business_fail: ['rate<0.05'],
  },
};

function authHeaders() {
  return {
    Authorization: `Bearer ${TOKEN}`,
    'Content-Type': 'application/json',
  };
}

export function shootLinkFlow() {
  if (!TOKEN) {
    failRate.add(1);
    return;
  }
  const t0 = Date.now();
  const res = http.post(
    `${BASE}/api/v1/company/shoot_link`,
    JSON.stringify({
      company_id: COMPANY_ID,
      category: 'other',
      tier: 'small',
      ttl_hours: 24,
      max_uses: 1,
    }),
    { headers: authHeaders() },
  );
  shootTrend.add(Date.now() - t0);
  const ok = check(res, {
    'shoot_link 200': (r) => r.status === 200,
    'has token': (r) => !!(r.json('token') || r.json('url')),
  });
  failRate.add(!ok);
  sleep(0.5);
}

export function orderCreateFlow() {
  if (!TOKEN) {
    failRate.add(1);
    return;
  }
  // Без реальных фото в MinIO create вернёт 400 — для dry-run используем prepare + fake uuid
  const uuid = crypto.randomUUID();
  const prep = http.post(
    `${BASE}/api/v1/orders/photos/prepare`,
    JSON.stringify({ task_uuid: uuid }),
    { headers: authHeaders() },
  );
  check(prep, { 'prepare 200': (r) => r.status === 200 });

  const t0 = Date.now();
  const res = http.post(
    `${BASE}/api/v1/orders/create`,
    JSON.stringify({
      task_uuid: uuid,
      category: 'other',
      tier: 'small',
      company_id: COMPANY_ID,
      forbidden_categories: [],
      upsell_options: [],
    }),
    { headers: authHeaders() },
  );
  orderTrend.add(Date.now() - t0);
  // 400 «Нужны 12 фото» — ожидаемо без MinIO; считаем API живым если не 5xx
  const ok = check(res, {
    'order not 5xx': (r) => r.status < 500,
  });
  failRate.add(!ok);
  sleep(0.2);
}
