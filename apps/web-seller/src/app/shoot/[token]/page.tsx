'use client';

import {
  Anchor,
  Button,
  Card,
  Center,
  FileInput,
  Group,
  Loader,
  Progress,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core';
import { IconCamera, IconCheck, IconDeviceMobile, IconUpload } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { use, useEffect, useState } from 'react';
import axios from 'axios';
import { API_URL, apiMessage } from '../../../services/api';

type ShootData = {
  token: string;
  task_uuid: string;
  angles: string[];
  uploads: { index: number; upload_url: string; label: string }[];
};

/** §3.15 — браузер: open app deep link или галерея 12 фото */
export default function ShootLinkPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = use(params);
  const [meta, setMeta] = useState<ShootData | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
    axios
      .get<ShootData>(`${API_URL}/shoot/${token}`)
      .then(({ data }) => setMeta(data))
      .catch((e) => notifications.show({ color: 'red', message: apiMessage(e, 'Ссылка недействительна') }));
  }, [token]);

  function openInApp() {
    // Universal Link (iOS/Android) + custom scheme fallback §3.15
    const httpsLink = `${window.location.origin}/shoot/${token}`;
    const custom = `kworkmob://open/shoot/${token}`;
    window.location.href = custom;
    window.setTimeout(() => {
      // если схема не сработала — остаёмся на странице галереи
    }, 800);
    notifications.show({
      color: 'blue',
      message: `Открываем приложение… (${httpsLink}). Если не установлено — загрузите 12 фото ниже.`,
    });
  }

  async function submit() {
    if (!meta || files.length !== 12) return;
    setBusy(true);
    setProgress(0);
    try {
      const form = new FormData();
      files.forEach((f) => form.append('files', f));
      await axios.post(`${API_URL}/shoot/${token}/upload`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (e.total) setProgress(Math.round((e.loaded / e.total) * 100));
        },
      });
      setDone(true);
      notifications.show({ color: 'teal', message: '12 фото загружены в MinIO' });
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  if (!meta) {
    return (
      <Center mih="100vh">
        <Loader color="brand" />
      </Center>
    );
  }

  return (
    <Center
      mih="100vh"
      p="md"
      style={{
        background:
          'radial-gradient(circle at 12% 18%, rgba(3,129,233,0.16), transparent 42%), radial-gradient(circle at 88% 78%, rgba(148,3,253,0.12), transparent 40%), #f9fafb',
      }}
    >
      <Stack maw={760} w="100%">
        <div>
          <Title
            order={2}
            style={{
              backgroundImage: 'linear-gradient(135deg, #0057b8, #9403fd)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Съёмка по ссылке
          </Title>
          <Text c="#6d6c77">
            task {meta.task_uuid.slice(0, 8)}… · ссылка {token.slice(0, 8)}…
          </Text>
        </div>

        {!done && (
          <Card withBorder bg="#fff" p="lg">
            <Stack gap="sm">
              <Text fw={600}>Есть приложение?</Text>
              <Text size="sm" c="#6d6c77">
                Откройте AR-съёмку в приложении (Deep Link §3.15). Иначе загрузите 12 готовых фото из галереи.
              </Text>
              <Group>
                <Button leftSection={<IconDeviceMobile size={16} />} onClick={openInApp}>
                  Открыть в приложении
                </Button>
                <Anchor href="https://play.google.com/store" target="_blank" size="sm">
                  Google Play
                </Anchor>
              </Group>
            </Stack>
          </Card>
        )}

        {done ? (
          <Card withBorder bg="#fff" p="xl">
            <Stack align="center">
              <ThemeIcon size={48} radius="xl" variant="light" color="teal">
                <IconCheck size={28} />
              </ThemeIcon>
              <Text fw={600}>Фото успешно загружены</Text>
            </Stack>
          </Card>
        ) : (
          <>
            <FileInput
              multiple
              accept="image/*"
              label="Альтернатива без приложения — 12 фото из галереи"
              placeholder="Выберите ровно 12 файлов"
              value={files}
              onChange={(value) => setFiles((value ?? []).slice(0, 12))}
              leftSection={<IconUpload size={16} />}
            />
            <SimpleGrid cols={{ base: 3, sm: 4 }}>
              {Array.from({ length: 12 }, (_, index) => (
                <Card key={index} withBorder p="xs" mih={110} bg="#fff">
                  <Center h="100%">
                    <Stack align="center" gap={4}>
                      <ThemeIcon variant="light" color={files[index] ? 'teal' : 'brand'}>
                        <IconCamera size={16} />
                      </ThemeIcon>
                      <Text size="xs" c="#6d6c77" ta="center">
                        {meta.angles?.[index] ?? `Ракурс ${index + 1}`}
                      </Text>
                    </Stack>
                  </Center>
                </Card>
              ))}
            </SimpleGrid>
            {busy && <Progress value={progress} animated />}
            <Button disabled={files.length !== 12} loading={busy} onClick={() => void submit()}>
              Отправить 12 фото
            </Button>
          </>
        )}
      </Stack>
    </Center>
  );
}
