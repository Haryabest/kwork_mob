'use client';

import {
  Alert,
  Button,
  Card,
  Checkbox,
  FileButton,
  Group,
  NumberInput,
  Progress,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
} from '@mantine/core';
import { IconCamera, IconCheck, IconUpload } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { SellerShell } from '../../../components/SellerShell';
import { PageHeader, Surface } from '../../../components/ui';
import { api, apiMessage } from '../../../services/api';

const ANGLES = [
  'Фронт',
  'Фронт-лево 30°',
  'Лево 60°',
  'Лево 90°',
  'Лево-тыл 120°',
  'Тыл-лево 150°',
  'Тыл',
  'Тыл-право 210°',
  'Право 240°',
  'Право 270°',
  'Право-фронт 300°',
  'Фронт-право 330°',
];

type Prep = {
  task_uuid: string;
  photos_prefix: string;
  uploads: { index: number; upload_url: string; key: string; content_type: string }[];
};

type Upsell = { code: string; title: string; amount_rub: number };

export default function NewOrderPage() {
  const router = useRouter();
  const [files, setFiles] = useState<(File | null)[]>(Array(12).fill(null));
  const [category, setCategory] = useState<string | null>('other');
  const [tier, setTier] = useState<string | null>('small');
  const [birthDate, setBirthDate] = useState('');
  const [promocode, setPromocode] = useState('');
  const [upsells, setUpsells] = useState<Upsell[]>([]);
  const [selectedUpsells, setSelectedUpsells] = useState<string[]>([]);
  const [scaleW, setScaleW] = useState<number | string>(0.3);
  const [scaleH, setScaleH] = useState<number | string>(0.5);
  const [scaleD, setScaleD] = useState<number | string>(0.2);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);

  const ready = files.every(Boolean);
  const needsAge = category === 'adult';

  useEffect(() => {
    api
      .get<{ items: Upsell[] }>('/orders/upsells')
      .then(({ data }) => setUpsells(data.items ?? []))
      .catch(() => undefined);
  }, []);

  async function submit() {
    if (!ready || !category || !tier) return;
    if (needsAge && !birthDate) {
      notifications.show({ color: 'red', message: 'Для 18+ укажите дату рождения' });
      return;
    }
    if (selectedUpsells.includes('real_scale') && (!scaleW || !scaleH || !scaleD)) {
      notifications.show({ color: 'red', message: 'Укажите размеры для масштаба 1:1' });
      return;
    }
    setBusy(true);
    setProgress(0);
    try {
      const { data: prep } = await api.post<Prep>('/orders/photos/prepare', {});
      const form = new FormData();
      files.forEach((f) => form.append('files', f!));
      await api.post(`/orders/photos/upload?task_uuid=${prep.task_uuid}`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (e.total) setProgress(Math.round((e.loaded / e.total) * 80));
        },
      });
      const { data: order } = await api.post<{
        id: number;
        status: string;
        confirmation_url?: string;
      }>('/orders/create', {
        category,
        tier,
        task_uuid: prep.task_uuid,
        photos_prefix: prep.photos_prefix,
        forbidden_categories: [],
        upsell_options: selectedUpsells,
        scale_calibration: selectedUpsells.includes('real_scale')
          ? { width: Number(scaleW), height: Number(scaleH), depth: Number(scaleD) }
          : undefined,
        birth_date: needsAge ? birthDate : undefined,
        promocode: promocode.trim() || undefined,
      });
      setProgress(100);
      if (order.status === 'awaiting_payment') {
        const pay = await api.post<{ confirmation_url?: string }>(`/orders/${order.id}/pay`);
        if (pay.data.confirmation_url) {
          window.location.href = pay.data.confirmation_url;
          return;
        }
      }
      notifications.show({ color: 'teal', message: `Заказ #${order.id}: ${order.status}` });
      router.push(`/orders/${order.id}`);
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e, String(e)) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <SellerShell>
      <PageHeader title="Новый заказ" description="12 ракурсов → MinIO → очередь генерации" />
      <Surface>
        <Stack gap="lg">
          <Group grow preventGrowOverflow={false} style={{ flexWrap: 'wrap' }}>
            <Select
              label="Категория"
              value={category}
              onChange={setCategory}
              data={[
                { value: 'clothing', label: 'Одежда' },
                { value: 'shoes', label: 'Обувь' },
                { value: 'electronics', label: 'Электроника' },
                { value: 'furniture', label: 'Мебель' },
                { value: 'decor', label: 'Декор' },
                { value: 'toys', label: 'Игрушки' },
                { value: 'adult', label: 'Интимные товары (18+)' },
                { value: 'other', label: 'Другое' },
              ]}
            />
            <Select
              label="Тариф"
              value={tier}
              onChange={setTier}
              data={[
                { value: 'small', label: 'Small — 2 990 ₽' },
                { value: 'large', label: 'Large — 5 990 ₽' },
              ]}
            />
          </Group>
          {needsAge && (
            <>
              <Alert color="grape" title="Подтверждение возраста">
                Подтвердите, что вам 18 лет. Введите дату рождения.
              </Alert>
              <TextInput
                type="date"
                label="Дата рождения"
                value={birthDate}
                onChange={(e) => setBirthDate(e.currentTarget.value)}
                required
                maw={280}
              />
            </>
          )}
          <TextInput
            label="Промокод"
            placeholder="Опционально"
            value={promocode}
            onChange={(e) => setPromocode(e.currentTarget.value)}
            maw={280}
          />
          <Stack gap="xs">
            <Text size="sm" fw={500}>
              Апсейлы
            </Text>
            {upsells.map((u) => (
              <Checkbox
                key={u.code}
                label={`${u.title} (+${u.amount_rub} ₽)`}
                checked={selectedUpsells.includes(u.code)}
                onChange={(e) => {
                  const on = e.currentTarget.checked;
                  setSelectedUpsells((prev) =>
                    on ? [...prev, u.code] : prev.filter((c) => c !== u.code),
                  );
                }}
              />
            ))}
            {selectedUpsells.includes('real_scale') && (
              <Group grow maw={480}>
                <NumberInput
                  label="Ширина, м"
                  value={scaleW}
                  onChange={setScaleW}
                  decimalScale={2}
                  step={0.01}
                  min={0.01}
                />
                <NumberInput
                  label="Высота, м"
                  value={scaleH}
                  onChange={setScaleH}
                  decimalScale={2}
                  step={0.01}
                  min={0.01}
                />
                <NumberInput
                  label="Глубина, м"
                  value={scaleD}
                  onChange={setScaleD}
                  decimalScale={2}
                  step={0.01}
                  min={0.01}
                />
              </Group>
            )}
          </Stack>
          <SimpleGrid cols={{ base: 2, sm: 3, md: 4 }} spacing="md">
            {ANGLES.map((label, index) => (
              <Card
                key={label}
                padding="sm"
                radius="md"
                withBorder={false}
                style={{ background: 'rgba(0,87,184,0.04)' }}
              >
                <Stack gap={6} align="center">
                  <ThemeIcon variant="light" color={files[index] ? 'teal' : 'brand'} size="lg">
                    {files[index] ? <IconCheck size={16} /> : <IconCamera size={16} />}
                  </ThemeIcon>
                  <Text size="xs" ta="center" c="#6d6c77">
                    {label}
                  </Text>
                  <FileButton
                    accept="image/*"
                    onChange={(f) => {
                      setFiles((prev) => {
                        const next = [...prev];
                        next[index] = f;
                        return next;
                      });
                    }}
                  >
                    {(props) => (
                      <Button {...props} size="compact-xs" variant="light" leftSection={<IconUpload size={12} />}>
                        Файл
                      </Button>
                    )}
                  </FileButton>
                </Stack>
              </Card>
            ))}
          </SimpleGrid>
          {busy && <Progress value={progress} />}
          <Button loading={busy} disabled={!ready} onClick={submit} w="fit-content">
            Создать заказ
          </Button>
        </Stack>
      </Surface>
    </SellerShell>
  );
}
