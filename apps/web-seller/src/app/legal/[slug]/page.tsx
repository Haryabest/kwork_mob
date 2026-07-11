'use client';

import { Anchor, Button, Container, Paper, Stack, Text, Title } from '@mantine/core';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { api } from '../../../services/api';

export default function LegalDocumentPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const [doc, setDoc] = useState<{ title: string; body: string; version: number } | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api
      .get(`/legal/${slug}`)
      .then(({ data }) => setDoc(data))
      .catch(() => setError('Документ не найден'));
  }, [slug]);

  return (
    <Container size="sm" py="xl">
      <Paper withBorder p="xl" radius="lg">
        <Stack>
          <Anchor component={Link} href="/register" size="sm">
            ← К регистрации
          </Anchor>
          {error && <Text c="red">{error}</Text>}
          {doc && (
            <>
              <div>
                <Title order={2}>{doc.title}</Title>
                <Text size="sm" c="dimmed">
                  Версия {doc.version}
                </Text>
              </div>
              <Text style={{ whiteSpace: 'pre-wrap' }}>{doc.body}</Text>
            </>
          )}
          <Button component={Link} href="/register" variant="light">
            Вернуться
          </Button>
        </Stack>
      </Paper>
    </Container>
  );
}
