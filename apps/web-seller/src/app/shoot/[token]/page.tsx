'use client';

import { Button, Card, Center, FileInput, SimpleGrid, Stack, Text, ThemeIcon, Title } from '@mantine/core';
import { IconCamera, IconUpload } from '@tabler/icons-react';
import { use, useState } from 'react';

export default function ShootLinkPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = use(params);
  const [files, setFiles] = useState<File[]>([]);
  return (
    <Center mih="100vh" p="md"><Stack maw={760} w="100%"><div><Title order={2}>Загрузите фотографии товара</Title><Text c="dimmed">Добавьте 12 фото с разных ракурсов · ссылка {token.slice(0, 8)}</Text></div>
      <FileInput multiple accept="image/*" label="Фотографии" placeholder="Выберите до 12 файлов" value={files} onChange={(value) => setFiles((value ?? []).slice(0, 12))} leftSection={<IconUpload size={16} />} />
      <SimpleGrid cols={{ base: 3, sm: 4 }}>{Array.from({ length: 12 }, (_, index) => <Card key={index} withBorder p="xs" mih={110}><Center h="100%"><Stack align="center" gap={4}><ThemeIcon variant="light" color={files[index] ? 'green' : 'gray'}><IconCamera size={16} /></ThemeIcon><Text size="xs" c="dimmed">{files[index]?.name ?? `Ракурс ${index + 1}`}</Text></Stack></Center></Card>)}</SimpleGrid>
      <Button disabled={files.length !== 12}>Отправить 12 фото</Button></Stack></Center>
  );
}
