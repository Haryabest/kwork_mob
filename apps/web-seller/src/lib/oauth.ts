'use client';

import { api, apiMessage } from '../services/api';

const CONSENT_SLUGS = ['terms', 'privacy', 'offer', 'rights', 'nsfw_rules'] as const;

export type OAuthProvider = { provider: string; label: string };

export async function fetchOAuthProviders(): Promise<OAuthProvider[]> {
  const { data } = await api.get<{ items: OAuthProvider[] }>('/auth/oauth/providers');
  return data.items ?? [];
}

export function webOAuthRedirectUri(): string {
  if (typeof window === 'undefined') return '';
  return `${window.location.origin}/auth/oauth/callback`;
}

export type OAuthIdentity = { provider: string; email?: string | null; linked_at?: string | null };

export async function fetchOAuthIdentities(): Promise<OAuthIdentity[]> {
  const { data } = await api.get<{ items: OAuthIdentity[] }>('/auth/oauth/identities');
  return data.items ?? [];
}

export async function startOAuthLink(provider: string): Promise<void> {
  const redirectUri = webOAuthRedirectUri();
  const { data } = await api.get<{ authorize_url: string; state: string }>(
    `/auth/oauth/${provider}/link`,
    { params: { platform: 'web', redirect_uri: redirectUri } },
  );
  if (typeof window !== 'undefined') {
    sessionStorage.setItem('oauth_state', data.state);
    sessionStorage.setItem('oauth_provider', provider);
    sessionStorage.setItem('oauth_redirect_uri', redirectUri);
    sessionStorage.setItem('oauth_flow', 'link');
  }
  window.location.href = data.authorize_url;
}

export async function completeOAuthLinkCallback(code: string, state: string): Promise<void> {
  const provider = sessionStorage.getItem('oauth_provider');
  const redirectUri = sessionStorage.getItem('oauth_redirect_uri') || webOAuthRedirectUri();
  const savedState = sessionStorage.getItem('oauth_state');
  if (!provider || state !== savedState) {
    throw new Error('Неверный OAuth state');
  }
  await api.post(`/auth/oauth/${provider}/link`, {
    code,
    state,
    redirect_uri: redirectUri,
  });
  sessionStorage.removeItem('oauth_state');
  sessionStorage.removeItem('oauth_provider');
  sessionStorage.removeItem('oauth_redirect_uri');
  sessionStorage.removeItem('oauth_flow');
}

export async function unlinkOAuth(provider: string): Promise<void> {
  await api.delete(`/auth/oauth/${provider}/link`);
}

export async function startOAuth(
  provider: string,
  mode: 'login' | 'register',
  consents?: string[],
): Promise<void> {
  const redirectUri = webOAuthRedirectUri();
  const params: Record<string, string> = {
    platform: 'web',
    mode,
    redirect_uri: redirectUri,
  };
  if (mode === 'register' && consents?.length) {
    params.consents = consents.join(',');
  }
  const { data } = await api.get<{ authorize_url: string; state: string }>(
    `/auth/oauth/${provider}/authorize`,
    { params },
  );
  if (typeof window !== 'undefined') {
    sessionStorage.setItem('oauth_state', data.state);
    sessionStorage.setItem('oauth_provider', provider);
    sessionStorage.setItem('oauth_redirect_uri', redirectUri);
    sessionStorage.setItem('oauth_flow', mode);
  }
  window.location.href = data.authorize_url;
}

export async function completeOAuthCallback(
  code: string,
  state: string,
): Promise<{ access_token: string; refresh_token: string; status?: string }> {
  const provider = sessionStorage.getItem('oauth_provider');
  const redirectUri = sessionStorage.getItem('oauth_redirect_uri') || webOAuthRedirectUri();
  const savedState = sessionStorage.getItem('oauth_state');
  if (!provider || state !== savedState) {
    throw new Error('Неверный OAuth state');
  }
  const { data } = await api.post<{
    access_token: string;
    refresh_token: string;
    status?: string;
  }>(`/auth/oauth/${provider}/callback`, {
    code,
    state,
    redirect_uri: redirectUri,
  });
  sessionStorage.removeItem('oauth_state');
  sessionStorage.removeItem('oauth_provider');
  sessionStorage.removeItem('oauth_redirect_uri');
  sessionStorage.removeItem('oauth_flow');
  return data;
}

export function getOAuthFlow(): string | null {
  if (typeof window === 'undefined') return null;
  return sessionStorage.getItem('oauth_flow');
}

export { CONSENT_SLUGS };

export function oauthErrorMessage(error: unknown): string {
  return apiMessage(error, 'Ошибка входа через соцсеть');
}
