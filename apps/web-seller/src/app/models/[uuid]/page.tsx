'use client';

import {
  Badge,
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
import { IconDownload, IconLink, IconShare2, IconStar } from '@tabler/icons-react';
import { useDisclosure } from '@mantine/hooks';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { notifications } from '@mantine/notifications';
import { SellerShell } from '../../../components/SellerShell';
import { PageHeader, Surface } from '../../../components/ui';
import { api, apiMessage } from '../../../services/api';

type PubLink = {
  id: number;
  marketplace: string;
  url: string;
  status: string;
  error_message?: string | null;
};

type Model = {
  uuid: string;
  order_id: number;
  glb_url?: string | null;
  usdz_url?: string | null;
  publish_status?: string;
  publication_links?: PubLink[];
  created_at?: string;
};

const PUBLISH_LABEL: Record<string, string> = {
  not_published: 'Не опубликована',
  published_wildberries: 'Опубликовано WB',
  published_ozon: 'Опубликовано Ozon',
  published_both: 'WB + Ozon',
  verified_wb: 'Верифицировано WB',
  verified_ozon: 'Верифицировано Ozon',
};

export default function ModelDetailPage() {
  const params = useParams<{ uuid: string }>();
  const uuid = params.uuid;
  const [model, setModel] = useState<Model | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [publishOpen, { open: openPublish, close: closePublish }] = useDisclosure(false);
  const [linkOpen, { open: openLink, close: closeLink }] = useDisclosure(false);
  const [marketplace, setMarketplace] = useState<string | null>('ozon');
  const [productUrl, setProductUrl] = useState('');
  const [rateOpen, { open: openRate, close: closeRate }] = useDisclosure(false);
  const [rating, setRating] = useState<string | null>('5');

  const load = useCallback(async () => {
    try {
      const { data } = await api.get<Model>(`/models/${uuid}`);
      setModel(data);
      try {
        const prev = await api.get<{ preview_url: string }>(`/models/${uuid}/preview`);
        setPreviewUrl(prev.data.preview_url);
      } catch {
        setPreviewUrl(null);
      }
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setLoading(false);
    }
  }, [uuid]);

  useEffect(() => {
    void load();
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

  async function markPublished() {
    if (!marketplace) return;
    setBusy(true);
    try {
      const { data } = await api.post<{ publish_status: string }>(`/models/${uuid}/publish/mark`, {
        marketplace,
      });
      notifications.show({ color: 'teal', message: `Статус: ${data.publish_status}` });
      closePublish();
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function addLink() {
    setBusy(true);
    try {
      const { data } = await api.post<{ status: string; error_message?: string }>(
        `/models/${uuid}/publication/links`,
        { url: productUrl },
      );
      notifications.show({
        color: data.status === 'verified' ? 'teal' : 'yellow',
        message: data.status === 'verified' ? 'Верификация успешна + бонус' : `Статус: ${data.status}`,
      });
      closeLink();
      setProductUrl('');
      await load();
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
        title="Модель"
        description={model.uuid}
        action={
          <Badge variant="light" color="brand" size="lg">
            {PUBLISH_LABEL[model.publish_status || ''] || model.publish_status || '—'}
          </Badge>
        }
      />

      <div
        style={{
          display: 'grid',
          gap: '1.5rem',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        }}
      >
        <Surface style={{ minHeight: 320 }}>
          <Title order={4} mb="md">
            Предпросмотр GLB
          </Title>
          {previewUrl ? (
            <model-viewer
              src={previewUrl}
              camera-controls
              touch-action="pan-y"
              style={{ width: '100%', height: 320, background: 'rgba(0,87,184,0.04)', borderRadius: 12 }}
            >
              <Text c="#6d6c77" ta="center" pt={120}>
                Загрузка 3D…
              </Text>
            </model-viewer>
          ) : (
            <Text c="#6d6c77" ta="center" py={100}>
              GLB ещё недоступен — дождитесь завершения генерации
            </Text>
          )}
          <Text size="xs" c="#6d6c77" mt="sm">
            Заказ #{model.order_id}
          </Text>
        </Surface>

        <Surface>
          <Title order={4} mb="md">
            Скачать и опубликовать
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
            <Button variant="light" leftSection={<IconLink size={16} />} onClick={openLink}>
              Добавить ссылку на карточку WB/Ozon
            </Button>
            <Button variant="light" leftSection={<IconShare2 size={16} />} onClick={openPublish}>
              Я опубликовал на маркетплейсе
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

          {(model.publication_links || []).length > 0 && (
            <Stack gap={6} mt="xl">
              <Text size="sm" fw={600}>
                Ссылки верификации
              </Text>
              {model.publication_links!.map((l) => (
                <Group key={l.id} justify="space-between" wrap="nowrap">
                  <Text size="xs" lineClamp={1} style={{ flex: 1 }}>
                    {l.marketplace}: {l.url}
                  </Text>
                  <Badge size="sm" color={l.status === 'verified' ? 'teal' : l.status === 'failed' ? 'red' : 'gray'}>
                    {l.status}
                  </Badge>
                </Group>
              ))}
            </Stack>
          )}

          <Stack gap={6} mt="xl">
            <Text size="sm" fw={600}>
              Инструкция
            </Text>
            <Text size="sm" c="#6d6c77">
              Ozon: Контент → 3D-модель → загрузить GLB.
            </Text>
            <Text size="sm" c="#6d6c77">
              Wildberries: Карточка товара → 3D → USDZ (или GLB, если USDZ ещё нет).
            </Text>
          </Stack>
        </Surface>
      </div>

      <Modal opened={linkOpen} onClose={closeLink} title="Ссылка на карточку товара" centered radius="lg">
        <Stack>
          <TextInput
            label="URL Wildberries или Ozon"
            placeholder="https://www.wildberries.ru/catalog/..."
            value={productUrl}
            onChange={(e) => setProductUrl(e.currentTarget.value)}
          />
          <Button loading={busy} onClick={() => void addLink()} disabled={productUrl.length < 12}>
            Проверить и сохранить
          </Button>
        </Stack>
      </Modal>

      <Modal opened={publishOpen} onClose={closePublish} title="Отметить публикацию" centered radius="lg">
        <Stack>
          <Select
            label="Маркетплейс"
            data={[
              { value: 'ozon', label: 'Ozon' },
              { value: 'wildberries', label: 'Wildberries' },
              { value: 'both', label: 'Оба' },
            ]}
            value={marketplace}
            onChange={setMarketplace}
          />
          <Button loading={busy} onClick={() => void markPublished()}>
            Подтвердить
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
    </SellerShell>
  );
}

declare global {
  namespace JSX {
    interface IntrinsicElements {
      'model-viewer': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        src?: string;
        'camera-controls'?: boolean;
        'touch-action'?: string;
      };
    }
  }
}
