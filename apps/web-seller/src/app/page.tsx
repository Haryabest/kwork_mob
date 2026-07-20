'use client';

import { Center, Loader } from '@mantine/core';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { AuthCard } from '../components/AuthCard';
import { api } from '../services/api';

/** §20.1 — чистая стартовая страница, только поп-ап входа */
export default function HomePage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    api
      .get<{ status?: string }>('/user/me')
      .then(({ data }) => {
        router.replace(data.status === 'pending_type' ? '/register/type' : '/dashboard');
      })
      .catch(() => setReady(true));
  }, [router]);

  if (!ready) {
    return (
      <Center mih="100vh" className="vz-canvas">
        <Loader color="brand" />
      </Center>
    );
  }

  return (
    <Center mih="100vh" p="md" className="vz-canvas">
      <AuthCard />
    </Center>
  );
}
