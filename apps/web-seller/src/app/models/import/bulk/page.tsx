'use client';

import {
  Alert,
  Button,
  FileInput,
  Group,
  Progress,
  Select,
  Stack,
  Text,
  Table,
} from '@mantine/core';
import { IconUpload } from '@tabler/icons-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { notifications } from '@mantine/notifications';
import axios from 'axios';
import { SellerShell } from '../../../../components/SellerShell';
import { PageHeader, ScrollTable, Surface } from '../../../../components/ui';
import { api, apiMessage } from '../../../../services/api';

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
const MAX_FILES = 100;
const BULK_MIN = 11;

type PrepItem = {
  model_uuid: string;
  key: string;
  upload_url: string;
  category?: string;
  display_name?: string | null;
};

export default function BulkImportModelsPage() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [category, setCategory] = useState<string | null>('other');
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [importPriceRub, setImportPriceRub] = useState<number | null>(null);
  const [resultRows, setResultRows] = useState<Array<{ uuid: string; order_id: number }>>([]);

  useEffect(() => {
    api
      .get<{ amount_rub: number }>('/models/import/price')
      .then(({ data }) => setImportPriceRub(data.amount_rub))
      .catch(() => {});
  }, []);

  function onFilesSelected(list: File[] | File | null) {
    if (!list) {
      setFiles([]);
      return;
    }
    const arr = Array.isArray(list) ? list : [list];
    const glbs = arr.filter((f) => f.name.toLowerCase().endsWith('.glb'));
    if (glbs.length !== arr.length) {
      notifications.show({ color: 'yellow', message: 'Только файлы .glb' });
    }
    if (glbs.length > MAX_FILES) {
      notifications.show({ color: 'red', message: `Максимум ${MAX_FILES} файлов` });
      setFiles(glbs.slice(0, MAX_FILES));
      return;
    }
    setFiles(glbs);
  }

  async function submit() {
    if (!category || files.length < BULK_MIN) return;
    for (const f of files) {
      if (f.size > MAX_BYTES) {
        notifications.show({ color: 'red', message: `${f.name} больше 50 МБ` });
        return;
      }
    }
    setBusy(true);
    setProgress(0);
    setResultRows([]);
    try {
      const { data: prep } = await api.post<{
        company_id: number;
        import_price_rub: number;
        total_price_rub: number;
        items: PrepItem[];
      }>('/models/import/bulk/prepare', {
        items: files.map((f) => ({
          category,
          display_name: f.name.replace(/\.glb$/i, ''),
        })),
      });

      const total = prep.items.length;
      for (let i = 0; i < total; i++) {
        const item = prep.items[i];
        const file = files[i];
        await axios.put(item.upload_url, file, {
          headers: { 'Content-Type': 'model/gltf-binary' },
        });
        setProgress(Math.round(((i + 1) / total) * 85));
      }

      const { data: bulk } = await api.post<{
        created: Array<{ uuid: string; order_id: number }>;
        errors: Array<{ model_uuid: string; error: string }>;
        total_charged_rub: number;
      }>('/models/import/bulk', {
        company_id: prep.company_id,
        items: prep.items.map((p, i) => ({
          glb_key: p.key,
          model_uuid: p.model_uuid,
          category,
          display_name: files[i].name.replace(/\.glb$/i, ''),
        })),
      });
      setProgress(100);
      setResultRows(bulk.created ?? []);
      if (bulk.errors?.length) {
        notifications.show({
          color: 'orange',
          message: `Импортировано ${bulk.created.length}, ошибок ${bulk.errors.length}`,
        });
      } else {
        notifications.show({
          color: 'teal',
          message: `Импортировано ${bulk.created.length} моделей · ${bulk.total_charged_rub} ₽`,
        });
      }
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  const totalPrice =
    importPriceRub != null && files.length > 0 ? importPriceRub * files.length : null;

  return (
    <SellerShell>
      <PageHeader
        title="Массовый импорт GLB"
        description={`§6.10 · от ${BULK_MIN} до ${MAX_FILES} моделей за раз · Owner / API key`}
        action={
          <Group>
            <Button component={Link} href="/models/import" variant="light">
              Один файл
            </Button>
            <Button component={Link} href="/models" variant="light">
              К списку
            </Button>
          </Group>
        }
      />
      <Surface>
        <Stack gap="md">
          <Alert color="blue" variant="light">
            Для 1–10 моделей используйте{' '}
            <Link href="/models/import">обычный импорт</Link>. Массовый режим — для ERP и больших
            партий (API: <code>POST /models/import/bulk/prepare</code> +{' '}
            <code>/models/import/bulk</code>, scope <code>import:create</code>).
          </Alert>
          {importPriceRub != null && (
            <Text size="sm" fw={600}>
              {importPriceRub > 0
                ? `Стоимость: ${importPriceRub} ₽ × файл${totalPrice != null ? ` · итого ${totalPrice} ₽` : ''}`
                : 'Импорт бесплатный'}
            </Text>
          )}
          <Select
            label="Категория для всех файлов"
            data={CATEGORY_OPTIONS}
            value={category}
            onChange={setCategory}
            size="md"
          />
          <FileInput
            label={`Файлы .glb (${BULK_MIN}–${MAX_FILES})`}
            accept=".glb,model/gltf-binary"
            value={files}
            onChange={onFilesSelected}
            leftSection={<IconUpload size={16} />}
            multiple
            size="md"
          />
          {files.length > 0 && (
            <Text size="sm" c="dimmed">
              Выбрано: {files.length} ·{' '}
              {(files.reduce((s, f) => s + f.size, 0) / (1024 * 1024)).toFixed(1)} MB суммарно
            </Text>
          )}
          {busy && <Progress value={progress} animated />}
          <Group>
            <Button
              loading={busy}
              disabled={!category || files.length < BULK_MIN}
              onClick={() => void submit()}
            >
              Импортировать {files.length > 0 ? files.length : ''} моделей
            </Button>
          </Group>
          {resultRows.length > 0 && (
            <ScrollTable>
              <Table miw={480}>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>UUID</Table.Th>
                    <Table.Th>Заказ</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {resultRows.map((r) => (
                    <Table.Tr key={r.uuid}>
                      <Table.Td>
                        <Text
                          component={Link}
                          href={`/models/${r.uuid}`}
                          c="brand"
                          fw={600}
                          style={{ textDecoration: 'none' }}
                        >
                          {r.uuid.slice(0, 8)}…
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text
                          component={Link}
                          href={`/orders/${r.order_id}`}
                          c="brand"
                          style={{ textDecoration: 'none' }}
                        >
                          #{r.order_id}
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </ScrollTable>
          )}
        </Stack>
      </Surface>
    </SellerShell>
  );
}
