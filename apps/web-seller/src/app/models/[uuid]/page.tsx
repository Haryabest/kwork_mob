'use client';

import {
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
  Loader,
  Center,
} from '@mantine/core';
import { IconDownload, IconShare2, IconStar, IconTrash, IconClock, IconLink } from '@tabler/icons-react';
import { useDisclosure } from '@mantine/hooks';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { notifications } from '@mantine/notifications';
import { SellerShell } from '../../../components/SellerShell';
import { ModelViewer3D } from '../../../components/ModelViewer3D';
import { PageHeader, Surface } from '../../../components/ui';
import { api, apiMessage, getPromoErrorMeta } from '../../../services/api';
import { loadModelPreviewBlobUrl, revokeModelPreviewUrl } from '../../../lib/modelPreview';

type Model = {
  uuid: string;
  order_id: number;
  display_name?: string | null;
  tier?: string | null;
  category?: string | null;
  glb_url?: string | null;
  usdz_url?: string | null;
  created_at?: string;
  storage?: {
    source_expires_at?: string;
    days_left?: number;
    source_extend_count?: number;
    extends_remaining?: number;
    max_extends?: number;
    in_trash?: boolean;
  };
};

export default function ModelDetailPage() {
  const params = useParams<{ uuid: string }>();
  const uuid = params.uuid;
  const [model, setModel] = useState<Model | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [rateOpen, { open: openRate, close: closeRate }] = useDisclosure(false);
  const [regenOpen, { open: openRegen, close: closeRegen }] = useDisclosure(false);
  const [promocode, setPromocode] = useState('');
  const [promoPreview, setPromoPreview] = useState<{
    discount_amount: number;
    final_amount: number;
    base_amount: number;
  } | null>(null);
  const [promoWarnOpen, { open: openPromoWarn, close: closePromoWarn }] = useDisclosure(false);
  const [promoWarnText, setPromoWarnText] = useState('');
  const [rating, setRating] = useState<string | null>('5');

  const load = useCallback(async () => {
    setLoading(true);
    setPreviewLoading(true);
    try {
      const { data } = await api.get<Model>(`/models/${uuid}`);
      setModel(data);
      setPreviewUrl((prev) => {
        revokeModelPreviewUrl(prev);
        return null;
      });
      const blobUrl = await loadModelPreviewBlobUrl(uuid);
      setPreviewUrl(blobUrl);
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
      setPreviewUrl(null);
    } finally {
      setLoading(false);
      setPreviewLoading(false);
    }
  }, [uuid]);

  useEffect(() => {
    void load();
    return () => {
      setPreviewUrl((prev) => {
        revokeModelPreviewUrl(prev);
        return null;
      });
    };
  }, [load]);

  async function download(format: 'glb' | 'usdz') {
    setBusy(true);
    try {
      const { data } = await api.get<{ download_url: string; message?: string }>(
        `/models/${uuid}/download`,
        { params: { format } },
      );
      if (data.message) notifications.show({ color: 'yellow', message: data.message });
      window.open(data.download_url, '_blank', 'noopener,noreferrer');
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function exportPublishZip() {
    setBusy(true);
    try {
      const { data } = await api.post<{ download_url: string; message?: string }>(
        `/models/${uuid}/export-publish-zip`,
      );
      notifications.show({
        color: 'teal',
        message: data.message || 'ZIP для публикации готов',
      });
      window.open(data.download_url, '_blank', 'noopener,noreferrer');
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function restoreSources() {
    setBusy(true);
    try {
      const { data } = await api.post<{ download_url: string; message?: string }>(
        `/models/${uuid}/restore-sources`,
      );
      notifications.show({
        color: 'teal',
        message: data.message || 'Presigned URL исходников готов',
      });
      window.open(data.download_url, '_blank', 'noopener,noreferrer');
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function validatePromo(tier: string) {
    const code = promocode.trim();
    if (!code) {
      setPromoPreview(null);
      return;
    }
    try {
      const { data } = await api.post<{
        discount_amount: number;
        final_amount: number;
        base_amount: number;
      }>('/promocodes/validate', { code, tier });
      setPromoPreview(data);
      notifications.show({
        color: 'teal',
        message: `Скидка ${data.discount_amount} ₽ → к оплате ${data.final_amount} ₽`,
      });
    } catch (e) {
      setPromoPreview(null);
      const meta = getPromoErrorMeta(e);
      notifications.show({ color: 'red', message: meta.message });
      if (meta.showWarning && meta.warningMessage) {
        setPromoWarnText(meta.warningMessage);
        openPromoWarn();
      }
    }
  }

  async function regenerate() {
    setBusy(true);
    try {
      const { data } = await api.post<{
        task_uuid: string;
        category: string;
        tier: string;
        company_id?: number;
      }>(`/models/${uuid}/regenerate`);
      const { data: order } = await api.post<{ id: number }>('/orders/create', {
        task_uuid: data.task_uuid,
        category: data.category,
        tier: data.tier,
        company_id: data.company_id,
        model_display_name:
          model?.display_name?.trim() || `Модель ${uuid.slice(0, 8)}`,
        promocode: promocode.trim() || undefined,
      });
      closeRegen();
      setPromocode('');
      setPromoPreview(null);
      notifications.show({ color: 'teal', message: `Заказ #${order.id} в очереди` });
      window.location.href = `/orders/${order.id}`;
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function extendStorage() {
    setBusy(true);
    try {
      const { data } = await api.post<{ message?: string; extends_remaining?: number }>(
        `/models/${uuid}/extend-storage`,
      );
      notifications.show({ color: 'teal', message: data.message || 'Хранение продлено' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function moveToTrash() {
    if (!window.confirm('Исходные фото и модель будут перемещены в корзину на 30 дней. Продолжить?')) {
      return;
    }
    setBusy(true);
    try {
      const { data } = await api.post<{ message?: string }>(`/models/${uuid}/trash`);
      notifications.show({ color: 'orange', message: data.message || 'В корзине' });
      window.location.href = '/models/trash';
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function createShare() {
    setBusy(true);
    try {
      const { data } = await api.post<{ url: string }>(`/models/${uuid}/share`, { ttl_days: 7 });
      await navigator.clipboard.writeText(data.url);
      notifications.show({ color: 'teal', message: `Ссылка скопирована: ${data.url}` });
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function submitRate() {
    setBusy(true);
    try {
      await api.post(`/models/${uuid}/rate`, { rating: Number(rating), reasons: [] });
      notifications.show({ color: 'teal', message: 'Спасибо за оценку' });
      closeRate();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  if (loading || !model) {
    return (
      <SellerShell>
        <Center py="xl">
          <Loader color="brand" />
        </Center>
      </SellerShell>
    );
  }

  return (
    <SellerShell>
      <PageHeader
        title={model.display_name?.trim() || 'Модель'}
        description={model.created_at ? new Date(model.created_at).toLocaleString('ru-RU') : undefined}
      />

      <div
        style={{
          display: 'grid',
          gap: '1.5rem',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        }}
      >
        <Surface style={{ minHeight: 400 }}>
          <Title order={4} mb="md">
            Предпросмотр
          </Title>
          {previewLoading ? (
            <Center py={100}>
              <Loader color="brand" size="sm" />
              <Text ml="sm" c="#6d6c77">
                Загрузка GLB…
              </Text>
            </Center>
          ) : previewUrl ? (
            <ModelViewer3D src={previewUrl} height={400} />
          ) : (
            <Text c="#6d6c77" ta="center" py={100}>
              GLB недоступен — перелогиньтесь или обновите страницу
            </Text>
          )}
        </Surface>

        <Surface>
          <Title order={4} mb="md">
            Скачать
          </Title>
          <Stack gap="sm">
            <Button leftSection={<IconDownload size={16} />} loading={busy} onClick={() => void download('glb')}>
              Скачать GLB (Ozon)
            </Button>
            <Button
              variant="light"
              leftSection={<IconDownload size={16} />}
              loading={busy}
              onClick={() => void download('usdz')}
            >
              Скачать USDZ (Wildberries)
            </Button>
            <Button
              variant="light"
              leftSection={<IconDownload size={16} />}
              loading={busy}
              onClick={() => void exportPublishZip()}
            >
              Экспортировать всё (ZIP)
            </Button>
            <Button variant="light" leftSection={<IconDownload size={16} />} loading={busy} onClick={() => void restoreSources()}>
              Восстановить исходники из облака
            </Button>
            <Button variant="light" loading={busy} onClick={openRegen}>
              Перегенерировать модель
            </Button>
            <Text size="xs" c="#6d6c77">
              Облачная копия:{' '}
              {model.storage?.days_left != null ? `${model.storage.days_left} дн.` : '—'} · продлений осталось{' '}
              {model.storage?.extends_remaining ?? '—'}/{model.storage?.max_extends ?? 3}
            </Text>
            <Button
              variant="light"
              leftSection={<IconClock size={16} />}
              loading={busy}
              disabled={(model.storage?.extends_remaining ?? 0) <= 0}
              onClick={() => void extendStorage()}
            >
              Продлить хранение (+30 дней)
            </Button>
            <Button
              variant="light"
              color="red"
              leftSection={<IconTrash size={16} />}
              loading={busy}
              onClick={() => void moveToTrash()}
            >
              Удалить (в корзину)
            </Button>
            <Button variant="light" leftSection={<IconShare2 size={16} />} loading={busy} onClick={() => void createShare()}>
              Поделиться (публичная ссылка)
            </Button>
            <Button component={Link} href={`/viewer/${uuid}`} variant="light" leftSection={<IconLink size={16} />}>
              Открыть просмотрщик
            </Button>
            <Button variant="subtle" leftSection={<IconStar size={16} />} onClick={openRate}>
              Оценить качество
            </Button>
          </Stack>
        </Surface>
      </div>

      <Modal
        opened={regenOpen}
        onClose={() => {
          closeRegen();
          setPromocode('');
          setPromoPreview(null);
        }}
        title="Перегенерация модели"
        centered
        radius="lg"
      >
        <Stack>
          <Text size="sm" c="dimmed">
            Будет создан новый заказ с теми же исходниками. Промокод необязателен.
          </Text>
          <TextInput
            label="Промокод"
            placeholder="Введите код"
            value={promocode}
            onChange={(e) => setPromocode(e.currentTarget.value.toUpperCase())}
          />
          <Group>
            <Button
              variant="light"
              disabled={!promocode.trim()}
              onClick={() => void validatePromo(model.tier || 'small')}
            >
              Проверить промокод
            </Button>
          </Group>
          {promoPreview && (
            <Text size="sm" c="teal">
              Скидка {promoPreview.discount_amount} ₽ · итого {promoPreview.final_amount} ₽ (было{' '}
              {promoPreview.base_amount} ₽)
            </Text>
          )}
          <Button loading={busy} onClick={() => void regenerate()}>
            Создать заказ на перегенерацию
          </Button>
        </Stack>
      </Modal>

      <Modal opened={rateOpen} onClose={closeRate} title="Оценка качества" centered radius="lg">
        <Stack>
          <Select label="Оценка" data={['1', '2', '3', '4', '5']} value={rating} onChange={setRating} />
          <Button loading={busy} onClick={() => void submitRate()}>
            Отправить
          </Button>
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
