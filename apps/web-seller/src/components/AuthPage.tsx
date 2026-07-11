import { Center, Stack, Text, Title } from '@mantine/core';
import type { ReactNode } from 'react';

export function AuthPage({ children }: { children: ReactNode }) {
  return (
    <Center mih="100vh" p="md" style={{ background: 'radial-gradient(circle at 15% 20%, rgba(11,122,115,.16), transparent 42%), #f4f7f7' }}>
      <Stack align="center" gap="lg" w={420} maw="100%">
        <div style={{ textAlign: 'center' }}>
          <Title order={1} c="brand">KWork Mob</Title>
          <Text c="dimmed">3D-модели для маркетплейсов</Text>
        </div>
        {children}
      </Stack>
    </Center>
  );
}
