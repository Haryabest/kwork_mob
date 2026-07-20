'use client';

import { Center, Loader, Text } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useEffect } from 'react';
import { completeOAuthCallback, completeOAuthLinkCallback, getOAuthFlow, oauthErrorMessage } from '../../../../lib/oauth';
import { api } from '../../../../services/api';

function OAuthCallbackInner() {
  const router = useRouter();
  const params = useSearchParams();

  useEffect(() => {
    const code = params.get('code');
    const state = params.get('state');
    const err = params.get('error');
    if (err) {
      notifications.show({ color: 'red', message: err });
      router.replace('/');
      return;
    }
    if (!code || !state) {
      notifications.show({ color: 'red', message: 'Нет code/state от провайдера' });
      router.replace('/');
      return;
    }
    (async () => {
      try {
        const flow = getOAuthFlow();
        if (flow === 'link') {
          await completeOAuthLinkCallback(code, state);
          const { data: meData } = await api.get<{ oauth_providers?: string[] }>('/user/me');
          sessionStorage.setItem('oauth_link_me', JSON.stringify(meData));
          notifications.show({ color: 'teal', message: 'Соцсеть привязана' });
          router.replace('/settings');
          return;
        }
        await completeOAuthCallback(code, state);
        const me = await api.get<{ status?: string }>('/user/me');
        router.replace(me.data.status === 'pending_type' ? '/register/type' : '/dashboard');
      } catch (error) {
        notifications.show({ color: 'red', message: oauthErrorMessage(error) });
        router.replace('/');
      }
    })();
  }, [params, router]);

  return (
    <Center mih="60vh">
      <Loader />
      <Text ml="md">Завершаем вход…</Text>
    </Center>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={<Center mih="60vh"><Loader /></Center>}>
      <OAuthCallbackInner />
    </Suspense>
  );
}
