'use client';

const SITE_KEY = process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY || '';
const SCRIPT_ID = 'recaptcha-v3';

export function recaptchaEnabled(): boolean {
  return Boolean(SITE_KEY);
}

function loadScript(): Promise<void> {
  if (typeof window === 'undefined') return Promise.resolve();
  const existing = document.getElementById(SCRIPT_ID);
  if (existing) {
    return new Promise((resolve) => {
      const g = (window as { grecaptcha?: { ready: (cb: () => void) => void } }).grecaptcha;
      if (g) g.ready(() => resolve());
      else existing.addEventListener('load', () => resolve(), { once: true });
    });
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.id = SCRIPT_ID;
    script.src = `https://www.google.com/recaptcha/api.js?render=${SITE_KEY}`;
    script.async = true;
    script.onload = () => {
      const g = (window as { grecaptcha?: { ready: (cb: () => void) => void } }).grecaptcha;
      if (g) g.ready(() => resolve());
      else resolve();
    };
    script.onerror = () => reject(new Error('recaptcha load failed'));
    document.head.appendChild(script);
  });
}

export async function getRecaptchaToken(action: string): Promise<string | undefined> {
  if (!SITE_KEY || typeof window === 'undefined') return undefined;
  await loadScript();
  const g = (window as {
    grecaptcha?: { execute: (key: string, opts: { action: string }) => Promise<string> };
  }).grecaptcha;
  if (!g) return undefined;
  return g.execute(SITE_KEY, { action });
}

export type LoginChallenge = {
  requires_captcha?: boolean;
  failures?: number;
  blocked?: boolean;
};

export function loginErrorDetail(error: unknown): LoginChallenge & { message?: string } {
  if (!error || typeof error !== 'object' || !('response' in error)) return {};
  const data = (error as { response?: { data?: { detail?: unknown } } }).response?.data;
  const detail = data?.detail;
  if (typeof detail === 'object' && detail !== null) {
    return detail as LoginChallenge & { message?: string };
  }
  if (typeof detail === 'string') return { message: detail };
  return {};
}
