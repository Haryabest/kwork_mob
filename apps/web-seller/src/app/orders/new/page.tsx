'use client';

import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  FileButton,
  Group,
  Modal,
  NumberInput,
  Progress,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
  UnstyledButton,
} from '@mantine/core';
import { IconCamera, IconCheck, IconUpload } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { useDisclosure } from '@mantine/hooks';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { SellerShell } from '../../../components/SellerShell';
import { PageHeader, Surface } from '../../../components/ui';
import { api, apiMessage, getPromoErrorMeta } from '../../../services/api';
import {
  photoUploadErrorMessage,
  shouldResetPhotoFiles,
  type PhotoUploadPhase,
} from '../../../lib/photoUpload';
import { uploadOrderPhotosSequential } from '../../../lib/uploadOrderPhotos';
import { normalizeImageFiles } from '../../../lib/normalizeImageFile';

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

const PHOTO_MODES = [
  { count: 1, title: '1 фото', hint: 'Быстрое оформление по одному снимку' },
  { count: 3, title: '3 фото', hint: 'Фронт и два боковых ракурса (120°)' },
  { count: 5, title: '5 фото', hint: 'Равномерно по кругу каждые 60°' },
  { count: 6, title: '6 фото', hint: 'Шесть ракурсов каждые 60°' },
] as const;

const VIEW_INDICES: Record<number, number[]> = {
  1: [0],
  3: [0, 4, 8],
  5: [0, 2, 4, 6, 8],
  6: [0, 2, 4, 6, 8, 10],
};

type Prep = {
  task_uuid: string;
  photo_count: number;
  photos_prefix: string;
  uploads: { index: number; upload_url: string; key: string; content_type: string }[];
};

type Upsell = { code: string; title: string; amount_rub: number };

type Me = {
  age_verified?: boolean;
  date_of_birth?: string | null;
};

function ageFromIso(iso: string): number | null {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  const today = new Date();
  let years = today.getFullYear() - d.getFullYear();
  const m = today.getMonth() - d.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < d.getDate())) years -= 1;
  return years;
}

export default function NewOrderPage() {
  const router = useRouter();
  const [photoCount, setPhotoCount] = useState<number | null>(null);
  const [files, setFiles] = useState<(File | null)[]>([]);
  const [category, setCategory] = useState<string | null>('other');
  const [tier, setTier] = useState<string | null>('small');
  const [modelName, setModelName] = useState('');
  const [birthDate, setBirthDate] = useState('');
  const [ageVerified, setAgeVerified] = useState(false);
  const [ageModal, setAgeModal] = useState(false);
  const [modalBirth, setModalBirth] = useState('');
  const [promocode, setPromocode] = useState('');
  const [upsells, setUpsells] = useState<Upsell[]>([]);
  const [selectedUpsells, setSelectedUpsells] = useState<string[]>([]);
  const [scaleW, setScaleW] = useState<number | string>(0.3);
  const [scaleH, setScaleH] = useState<number | string>(0.5);
  const [scaleD, setScaleD] = useState<number | string>(0.2);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [promoWarnOpen, { open: openPromoWarn, close: closePromoWarn }] = useDisclosure(false);
  const [promoWarnText, setPromoWarnText] = useState('');
  const [uploadError, setUploadError] = useState<string | null>(null);

  const uploadSlots = photoCount ? VIEW_INDICES[photoCount] ?? [] : [];
  const ready = photoCount !== null && files.length === uploadSlots.length && files.every(Boolean);
  const needsAge = category === 'adult' && !ageVerified;

  function selectPhotoMode(count: number) {
    setPhotoCount(count);
    setFiles(Array(VIEW_INDICES[count].length).fill(null));
    setUploadError(null);
  }

  useEffect(() => {
    api
      .get<{ items: Upsell[] }>('/orders/upsells')
      .then(({ data }) => setUpsells(data.items ?? []))
      .catch(() => undefined);
    api
      .get<Me>('/user/me')
      .then(({ data }) => {
        if (data.age_verified) {
          setAgeVerified(true);
          if (data.date_of_birth) setBirthDate(data.date_of_birth);
        }
      })
      .catch(() => undefined);
  }, []);

  function onCategoryChange(v: string | null) {
    setCategory(v);
    if (v === 'adult' && !ageVerified) {
      setModalBirth(birthDate);
      setAgeModal(true);
    }
  }

  function confirmAgeModal() {
    if (!modalBirth) {
      notifications.show({ color: 'red', message: 'Введите дату рождения' });
      return;
    }
    const years = ageFromIso(modalBirth);
    if (years == null) {
      notifications.show({ color: 'red', message: 'Некорректная дата' });
      return;
    }
    if (years < 18) {
      notifications.show({ color: 'red', message: 'Создание модели доступно только с 18 лет' });
      setCategory('other');
      setAgeModal(false);
      return;
    }
    setBirthDate(modalBirth);
    setAgeModal(false);
  }

  async function submit() {
    if (!ready || !category || !tier || photoCount === null) return;
    if (!modelName.trim()) {
      notifications.show({ color: 'red', message: 'Укажите название модели' });
      return;
    }
    if (needsAge && !birthDate) {
      setAgeModal(true);
      notifications.show({ color: 'red', message: 'Для 18+ укажите дату рождения' });
      return;
    }
    if (selectedUpsells.includes('real_scale') && (!scaleW || !scaleH || !scaleD)) {
      notifications.show({ color: 'red', message: 'Укажите размеры для масштаба 1:1' });
      return;
    }
    setBusy(true);
    setProgress(0);
    setUploadError(null);
    let phase: PhotoUploadPhase = 'prepare';
    try {
      const { data: prep } = await api.post<Prep>('/orders/photos/prepare', {
        photo_count: photoCount,
      });
      phase = 'upload';
      const normalized = await normalizeImageFiles(files);
      await uploadOrderPhotosSequential(prep, normalized, (p) => setProgress(p));
      phase = 'create';
      const { data: order } = await api.post<{
        id: number;
        status: string;
        confirmation_url?: string;
      }>('/orders/create', {
        category,
        tier,
        photo_count: photoCount,
        model_display_name: modelName.trim(),
        task_uuid: prep.task_uuid,
        photos_prefix: prep.photos_prefix,
        forbidden_categories: [],
        upsell_options: selectedUpsells,
        scale_calibration: selectedUpsells.includes('real_scale')
          ? { width: Number(scaleW), height: Number(scaleH), depth: Number(scaleD) }
          : undefined,
        birth_date: needsAge || (category === 'adult' && birthDate) ? birthDate || undefined : undefined,
        promocode: promocode.trim() || undefined,
        device_model: (() => {
          const ua = typeof navigator !== 'undefined' ? navigator.userAgent : '';
          const low = ua.toLowerCase();
          if (/iphone|ipad/.test(low)) return 'iOS Web';
          if (/android/.test(low)) return 'Android Web';
          if (/windows/.test(low)) return 'Windows';
          if (/mac os|macintosh/.test(low)) return 'macOS';
          if (/linux/.test(low)) return 'Linux';
          return 'web';
        })(),
        os_version: (() => {
          const ua = typeof navigator !== 'undefined' ? navigator.userAgent : '';
          const m = ua.match(/\(([^)]+)\)/);
          return (m?.[1] || ua).slice(0, 64);
        })(),
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
      if (phase === 'prepare' || phase === 'upload') {
        const msg = photoUploadErrorMessage(e, phase);
        setUploadError(msg);
        notifications.show({ color: 'red', message: msg, autoClose: 8000 });
        if (shouldResetPhotoFiles(e, phase)) {
          setFiles(Array(uploadSlots.length).fill(null));
        }
        return;
      }
      if (phase === 'create' && shouldResetPhotoFiles(e, 'create')) {
        const msg = photoUploadErrorMessage(e, 'create');
        setUploadError(msg);
        notifications.show({ color: 'red', message: msg, autoClose: 8000 });
        setFiles(Array(uploadSlots.length).fill(null));
        return;
      }
      const meta = getPromoErrorMeta(e);
      notifications.show({ color: 'red', message: meta.message });
      if (meta.showWarning && meta.warningMessage) {
        setPromoWarnText(meta.warningMessage);
        openPromoWarn();
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <SellerShell>
      <PageHeader
        title="Новый заказ"
        description="Выберите режим съёмки, загрузите фото и создайте заказ"
      />
      <Surface>
        <Stack gap="lg">
          <Group grow preventGrowOverflow={false} style={{ flexWrap: 'wrap' }}>
            <Select
              label="Категория"
              value={category}
              onChange={onCategoryChange}
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
          <TextInput
            label="Название модели"
            placeholder="Например: Кроссовки Nike Air Max"
            value={modelName}
            onChange={(e) => setModelName(e.currentTarget.value)}
            required
            maxLength={120}
            maw={480}
          />
          {category === 'adult' && (
            <>
              {ageVerified ? (
                <Alert color="teal" title="Возраст подтверждён">
                  <Group gap="xs">
                    <Badge color="teal">18+</Badge>
                    <Text size="sm">Повторный ввод даты рождения не требуется.</Text>
                  </Group>
                </Alert>
              ) : (
                <>
                  <Alert color="grape" title="Подтверждение возраста (§10.8.3)">
                    Подтвердите, что вам 18 лет. Введите дату рождения.
                  </Alert>
                  <TextInput
                    type="date"
                    label="Дата рождения"
                    value={birthDate}
                    onChange={(e) => setBirthDate(e.currentTarget.value)}
                    required
                    maw={280}
                    description="Сохраняется в профиле после успешной проверки"
                  />
                </>
              )}
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
          <Stack gap="xs">
            <Text size="sm" fw={500}>
              Режим съёмки
            </Text>
            <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md">
              {PHOTO_MODES.map((mode) => {
                const selected = photoCount === mode.count;
                return (
                  <UnstyledButton key={mode.count} onClick={() => selectPhotoMode(mode.count)}>
                    <Card
                      padding="md"
                      radius="md"
                      withBorder
                      style={{
                        borderColor: selected ? 'var(--mantine-color-brand-5)' : undefined,
                        background: selected ? 'rgba(0,87,184,0.08)' : 'rgba(0,87,184,0.04)',
                      }}
                    >
                      <Stack gap={4}>
                        <Group gap="xs">
                          <Text fw={600}>{mode.title}</Text>
                          {selected && (
                            <Badge size="xs" color="brand">
                              выбрано
                            </Badge>
                          )}
                        </Group>
                        <Text size="xs" c="#6d6c77">
                          {mode.hint}
                        </Text>
                      </Stack>
                    </Card>
                  </UnstyledButton>
                );
              })}
            </SimpleGrid>
          </Stack>
          {photoCount !== null && (
            <>
              {uploadError && (
                <Alert color="red" title="Загрузка фото" withCloseButton onClose={() => setUploadError(null)}>
                  {uploadError}
                </Alert>
              )}
              <Alert color="blue" variant="light">
                Загрузите {photoCount} {photoCount === 1 ? 'фото' : 'фото'} — остальные ракурсы
                заполнятся автоматически.
              </Alert>
              <SimpleGrid cols={{ base: 2, sm: 3, md: 4 }} spacing="md">
                {uploadSlots.map((viewIndex, slotIndex) => {
                  const label = ANGLES[viewIndex];
                  return (
                    <Card
                      key={`${photoCount}-${viewIndex}`}
                      padding="sm"
                      radius="md"
                      withBorder={false}
                      style={{ background: 'rgba(0,87,184,0.04)' }}
                    >
                      <Stack gap={6} align="center">
                        <ThemeIcon
                          variant="light"
                          color={files[slotIndex] ? 'teal' : 'brand'}
                          size="lg"
                        >
                          {files[slotIndex] ? <IconCheck size={16} /> : <IconCamera size={16} />}
                        </ThemeIcon>
                        <Text size="xs" ta="center" c="#6d6c77">
                          {label}
                        </Text>
                        <FileButton
                          accept="image/*"
                          capture="environment"
                          onChange={(f) => {
                            setUploadError(null);
                            setFiles((prev) => {
                              const next = [...prev];
                              next[slotIndex] = f;
                              return next;
                            });
                          }}
                        >
                          {(props) => (
                            <Button
                              {...props}
                              size="compact-xs"
                              variant="light"
                              leftSection={<IconUpload size={12} />}
                            >
                              Файл
                            </Button>
                          )}
                        </FileButton>
                      </Stack>
                    </Card>
                  );
                })}
              </SimpleGrid>
            </>
          )}
          {busy && <Progress value={progress} />}
          <Button
            loading={busy}
            disabled={!ready}
            onClick={submit}
            w="fit-content"
          >
            Создать заказ
          </Button>
        </Stack>
      </Surface>

      <Modal
        opened={ageModal}
        onClose={() => {
          setAgeModal(false);
          if (!birthDate && !ageVerified) setCategory('other');
        }}
        title="Подтвердите, что вам 18 лет"
        centered
      >
        <Stack>
          <Text size="sm">Введите дату рождения. При возрасте &lt;18 создание модели блокируется.</Text>
          <TextInput
            type="date"
            label="Дата рождения"
            value={modalBirth}
            onChange={(e) => setModalBirth(e.currentTarget.value)}
            required
          />
          <Group justify="flex-end">
            <Button
              variant="default"
              onClick={() => {
                setAgeModal(false);
                setCategory('other');
              }}
            >
              Отмена
            </Button>
            <Button onClick={confirmAgeModal}>Подтвердить</Button>
          </Group>
        </Stack>
      </Modal>

      <Modal opened={promoWarnOpen} onClose={closePromoWarn} title="Предупреждение" centered>
        <Stack>
          <Text size="sm">{promoWarnText}</Text>
          <Button onClick={closePromoWarn}>Понятно</Button>
        </Stack>
      </Modal>
    </SellerShell>
  );
}
