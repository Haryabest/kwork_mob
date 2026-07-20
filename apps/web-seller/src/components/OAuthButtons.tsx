'use client';

import { Button, Divider, Stack, Text } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';
import { CONSENT_SLUGS, fetchOAuthProviders, oauthErrorMessage, resolveOAuthCompanyId, startOAuth, type OAuthProvider } from '../lib/oauth';

type Props = {
  mode: 'login' | 'register';
  consents?: Record<string, boolean>;
  disabled?: boolean;
};

export function OAuthButtons({ mode, consents, disabled }: Props) {
  const [providers, setProviders] = useState<OAuthProvider[]>([]);
  const [loading, setLoading] = useState<string | null>(null);

  useEffect(() => {
    fetchOAuthProviders()
      .then(setProviders)
      .catch(() => setProviders([]));
  }, []);

  if (!providers.length) return null;

  async function onProvider(provider: string) {
    if (mode === 'register') {
      if (!consents || !CONSENT_SLUGS.every((s) => consents[s])) {
        notifications.show({ color: 'red', message: 'Примите все обязательные согласия' });
        return;
      }
    }
    setLoading(provider);
    try {
      const companyId = await resolveOAuthCompanyId();
      await startOAuth(
        provider,
        mode,
        mode === 'register' ? CONSENT_SLUGS.filter((s) => consents?.[s]) : undefined,
        companyId,
      );
    } catch (error) {
      notifications.show({ color: 'red', message: oauthErrorMessage(error) });
      setLoading(null);
    }
  }

  return (
    <Stack gap="sm">
      <Divider label="или" labelPosition="center" />
      <Text size="sm" c="dimmed" ta="center">
        Войти через
      </Text>
      <Stack gap="xs">
        {providers.map((p) => (
          <Button
            key={p.provider}
            variant="light"
            loading={loading === p.provider}
            disabled={disabled || (loading !== null && loading !== p.provider)}
            onClick={() => void onProvider(p.provider)}
          >
            {p.label}
          </Button>
        ))}
      </Stack>
    </Stack>
  );
}
