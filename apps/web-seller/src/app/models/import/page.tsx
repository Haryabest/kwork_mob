'use client';

import {
  Button,
  FileInput,
  Group,
  Progress,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { IconUpload } from '@tabler/icons-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { notifications } from '@mantine/notifications';
import axios from 'axios';
import { SellerShell } from '../../../components/SellerShell';
import { PageHeader, Surface } from '../../../components/ui';
import { api, apiMessage } from '../../../services/api';

const CATEGORY_OPTIONS = [
  { value: 'clothing', label: 'Одежда' },
  { value: 'shoes', label: 'Обувь' },
  { value: 'electronics', label: 'Электроника' },
  { value: 'furniture', label: 'Мебель' },
  { value: 'decor', label: 'Декор / Интерьер' },
  { value: 'toys', label: 'Игрушки' },
  { value: 'adult', label: '18+' },
  { value: 'other', label: 'Другое' },
];

const MAX_BYTES = 50 * 1024 * 1024;

export default function ImportModelPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [category, setCategory] = useState<string | null>('other');
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);

  async function submit() {
    if (!file || !category) return;
    if (file.size > MAX_BYTES) {
      notifications.show({ color: 'red', message: 'Файл больше 50 МБ (§6.10)' });
      return;
    }
    setBusy(true);
    setProgress(0);
    try {
      const { data: prep } = await api.post<{
        upload_url: string;
        key: string;
        model_uuid: string;
        company_id: number;
      }>('/models/import/prepare');

      await axios.put(prep.upload_url, file, {
        headers: { 'Content-Type': 'model/gltf-binary' },
        onUploadProgress: (e) => {
          if (e.total) setProgress(Math.round((e.loaded / e.total) * 80));
        },
      });
      setProgress(85);

      const { data: imported } = await api.post<{ uuid: string; order_id: number; status: string }>(
        '/models/import',
        {
          glb_key: prep.key,
          company_id: prep.company_id,
          model_uuid: prep.model_uuid,
          category,
          display_name: displayName.trim() || undefined,
        },
      );
      setProgress(100);
      if (imported.status === 'import_validating') {
        notifications.show({ color: 'blue', message: 'Модель на проверке (GLB / PBR / Draco)…' });
        router.push(`/orders/${imported.order_id}`);
        return;
      }
      notifications.show({ color: 'teal', message: 'Модель импортирована' });
      router.push(`/models/${imported.uuid}`);
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <SellerShell>
      <PageHeader
        title="Импорт модели"
        description="Готовый GLB до 50 МБ · только Owner компании §6.10"
        action={
          <Button component={Link} href="/models" variant="light">
            К списку
          </Button>
        }
      />
      <Surface>
        <Stack gap="md" maw={520}>
          <Text size="sm" c="dimmed">
            Модель сохраняется как external import — без генерации TRELLIS. После валидации доступна
            для скачивания и публикации как обычная.
          </Text>
          <TextInput
            label="Название"
            value={displayName}
            onChange={(e) => setDisplayName(e.currentTarget.value)}
            size="md"
          />
          <Select
            label="Категория"
            data={CATEGORY_OPTIONS}
            value={category}
            onChange={setCategory}
            size="md"
          />
          <FileInput
            label="Файл .glb"
            accept=".glb,model/gltf-binary"
            value={file}
            onChange={setFile}
            leftSection={<IconUpload size={16} />}
            size="md"
          />
          {file && (
            <Text size="sm" c="dimmed">
              {(file.size / (1024 * 1024)).toFixed(1)} MB
            </Text>
          )}
          {busy && <Progress value={progress} animated />}
          <Group>
            <Button loading={busy} disabled={!file || !category} onClick={() => void submit()}>
              Импортировать
            </Button>
          </Group>
        </Stack>
      </Surface>
    </SellerShell>
  );
}
