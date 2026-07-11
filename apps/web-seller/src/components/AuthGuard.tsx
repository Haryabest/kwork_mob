'use client';

import { Center, Loader } from '@mantine/core';
import { useRouter } from 'next/navigation';
import { type ReactNode, useEffect, useState } from 'react';
import { auth } from '../lib/auth';
import { api } from '../services/api';

export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!auth.getAccessToken()) {
        router.replace('/');
        return;
      }
      try {
        const { data } = await api.get<{ status?: string }>('/user/me');
        if (cancelled) return;
        if (data.status === 'pending_type') {
          router.replace('/register/type');
          return;
        }
        setAllowed(true);
      } catch {
        auth.clear();
        router.replace('/');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (!allowed) {
    return (
      <Center mih="100vh">
        <Loader color="brand" />
      </Center>
    );
  }
  return <>{children}</>;
}
