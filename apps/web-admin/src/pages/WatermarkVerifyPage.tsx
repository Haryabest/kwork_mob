import { useState } from 'react';
import {
  Badge,
  Button,
  Card,
  Code,
  FileInput,
  Group,
  Stack,
  Tabs,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconShieldCheck, IconUpload } from '@tabler/icons-react';
import { api, getApiError } from '../services/api';

type VerifyResult = {
  ok?: boolean;
  hmac_valid?: boolean;
  error?: string;
  user_id?: number;
  company_id?: number | null;
  order_id?: number;
  timestamp?: number;
  watermark?: string;
  extras?: Record<string, unknown>;
};

/** Проверка DWT/HMAC водяного знака §5.12 / §11.2 */
export default function WatermarkVerifyPage() {
  const [file, setFile] = useState<File | null>(null);
  const [bucket, setBucket] = useState('models');
  const [key, setKey] = useState('');
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [busy, setBusy] = useState(false);

  async function verifyUpload() {
    if (!file) {
      notifications.show({ color: 'yellow', message: 'Выберите GLB файл' });
      return;
    }
    setBusy(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const { data } = await api.post<VerifyResult>('/admin/watermark/verify-upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setResult(data);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setBusy(false);
    }
  }

  async function verifyMinio() {
    if (!bucket.trim() || !key.trim()) {
      notifications.show({ color: 'yellow', message: 'Укажите bucket и key' });
      return;
    }
    setBusy(true);
    try {
      const { data } = await api.post<VerifyResult>('/admin/watermark/verify-minio', {
        bucket: bucket.trim(),
        key: key.trim(),
      });
      setResult(data);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setBusy(false);
    }
  }

  const valid = result?.ok === true || result?.hmac_valid === true;

  return (
    <div className="vz-page">
      <div className="vz-page-header">
        <div>
          <Title order={2}>Watermark verify</Title>
          <Text c="#6d6c77" size="sm" mt={6}>
            Проверка HMAC/DWT в GLB · §5.12 / §11.2
          </Text>
        </div>
      </div>

      <Tabs defaultValue="upload">
        <Tabs.List>
          <Tabs.Tab value="upload" leftSection={<IconUpload size={16} />}>
            Загрузка GLB
          </Tabs.Tab>
          <Tabs.Tab value="minio" leftSection={<IconShieldCheck size={16} />}>
            MinIO объект
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="upload" pt="md">
          <Card withBorder p="md">
            <Stack gap="md">
              <FileInput
                label="GLB файл"
                accept=".glb,model/gltf-binary"
                value={file}
                onChange={setFile}
                clearable
              />
              <Button loading={busy} onClick={() => void verifyUpload()}>
                Проверить
              </Button>
            </Stack>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="minio" pt="md">
          <Card withBorder p="md">
            <Stack gap="md">
              <TextInput label="Bucket" value={bucket} onChange={(e) => setBucket(e.currentTarget.value)} />
              <TextInput
                label="Key"
                placeholder="orders/123/model.glb"
                value={key}
                onChange={(e) => setKey(e.currentTarget.value)}
              />
              <Button loading={busy} onClick={() => void verifyMinio()}>
                Проверить
              </Button>
            </Stack>
          </Card>
        </Tabs.Panel>
      </Tabs>

      {result && (
        <Card withBorder p="md" mt="md">
          <Group mb="sm">
            <Text fw={600}>Результат</Text>
            <Badge color={valid ? 'green' : 'red'}>{valid ? 'VALID' : 'INVALID'}</Badge>
          </Group>
          {result.error && (
            <Text c="red" size="sm" mb="sm">
              {result.error}
            </Text>
          )}
          <Stack gap={4}>
            <Text size="sm">user_id: {result.user_id ?? '—'}</Text>
            <Text size="sm">company_id: {result.company_id ?? '—'}</Text>
            <Text size="sm">order_id: {result.order_id ?? '—'}</Text>
            <Text size="sm">timestamp: {result.timestamp ?? '—'}</Text>
            <Text size="sm">watermark: {result.watermark ?? '—'}</Text>
          </Stack>
          {result.extras && (
            <Code block mt="md" style={{ whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(result.extras, null, 2)}
            </Code>
          )}
        </Card>
      )}
    </div>
  );
}
