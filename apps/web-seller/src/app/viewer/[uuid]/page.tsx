'use client';

import {
  Button,
  Divider,
  Group,
  Loader,
  Menu,
  Modal,
  Radio,
  Stack,
  Text,
  TextInput,
  Tooltip,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconArrowLeft,
  IconDownload,
  IconRefresh,
  IconSparkles,
  IconStar,
} from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ModelViewer3D } from '../../../components/ModelViewer3D';
import { loadModelPreviewBlobUrl, revokeModelPreviewUrl } from '../../../lib/modelPreview';
import { api, apiMessage } from '../../../services/api';
import styles from './viewer.module.css';

type ModelMeta = {
  uuid: string;
  display_name?: string | null;
  tier?: string | null;
  category?: string | null;
};

type PromoPreview = {
  discount_amount: number;
  final_amount: number;
  base_amount: number;
};

const BEIGE = '#f5f0e6';
const DEFAULT_PRICE = 2990;

const REGEN_MODES = [
  {
    value: '1',
    label: 'Генерация по 1 фотографии',
    hint: 'Сфотографируйте лицевую (фронтальную) часть объекта — она должна быть хорошо освещена и занимать большую часть кадра.',
  },
  {
    value: '3',
    label: 'Генерация по 3 фотографиям',
    hint: 'Смещайте угол съёмки на 120° относительно каждого предыдущего кадра — получится обход объекта по кругу.',
  },
  {
    value: '5',
    label: 'Генерация по 5 фотографиям',
    hint: 'Равномерно обойдите объект: смещение между кадрами примерно 72°. Добавьте ракурсы сверху/снизу при необходимости.',
  },
  {
    value: '6',
    label: 'Генерация по 6 фотографиям (крупные объекты)',
    hint: 'Снимите четыре угла, затем фото спереди и сзади. Подходит для дивана и другой крупной мебели.',
  },
] as const;

const UNSUPPORTED_FORMATS = new Set(['gltf', 'ply', 'stl', 'usd', 'usda', 'usdc']);

export default function ViewerPage() {
  const params = useParams<{ uuid: string }>();
  const router = useRouter();
  const uuid = params.uuid;

  const [url, setUrl] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [model, setModel] = useState<ModelMeta | null>(null);
  const [busy, setBusy] = useState(false);
  const [balance, setBalance] = useState<number | null>(null);

  const [rateOpen, { open: openRate, close: closeRate }] = useDisclosure(false);
  const [regenOpen, { open: openRegen, close: closeRegen }] = useDisclosure(false);
  const [topupOpen, { open: openTopup, close: closeTopup }] = useDisclosure(false);

  const [rating, setRating] = useState('5');
  const [regenMode, setRegenMode] = useState<string>('3');
  const [promocode, setPromocode] = useState('');
  const [promoPreview, setPromoPreview] = useState<PromoPreview | null>(null);
  const [topupAmount, setTopupAmount] = useState<number | string>(DEFAULT_PRICE);
  const [topupShortage, setTopupShortage] = useState(0);
  const [paying, setPaying] = useState(false);

  const displayName = model?.display_name?.trim() || 'Без названия';
  const payAmount = promoPreview?.final_amount ?? DEFAULT_PRICE;

  const regenHint = useMemo(
    () => REGEN_MODES.find((m) => m.value === regenMode)?.hint ?? '',
    [regenMode],
  );

  const loadMeta = useCallback(async () => {
    try {
      const [modelRes, meRes] = await Promise.all([
        api.get<ModelMeta>(`/models/${uuid}`),
        api.get<{ balance: number }>('/user/me').catch(() => ({ data: { balance: 0 } })),
      ]);
      setModel(modelRes.data);
      setBalance(meRes.data.balance ?? 0);
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }, [uuid]);

  useEffect(() => {
    void loadMeta();
  }, [loadMeta]);

  useEffect(() => {
    let blobUrl: string | null = null;
    (async () => {
      try {
        blobUrl = await loadModelPreviewBlobUrl(uuid);
        if (blobUrl) setUrl(blobUrl);
        else setErr('GLB недоступен');
      } catch (e) {
        setErr(apiMessage(e));
      } finally {
        setLoading(false);
      }
    })();
    return () => revokeModelPreviewUrl(blobUrl);
  }, [uuid]);

  async function download(format: string) {
    if (UNSUPPORTED_FORMATS.has(format)) {
      notifications.show({
        color: 'yellow',
        message: `Формат ${format.toUpperCase()} скоро будет доступен для скачивания`,
      });
      return;
    }
    if (format !== 'glb' && format !== 'usdz') return;
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

  async function validatePromo() {
    const code = promocode.trim();
    if (!code) {
      setPromoPreview(null);
      return;
    }
    try {
      const { data } = await api.post<PromoPreview>('/promocodes/validate', {
        code,
        tier: model?.tier || 'small',
      });
      setPromoPreview(data);
      notifications.show({
        color: 'teal',
        message: `Скидка ${data.discount_amount} ₽ → к оплате ${data.final_amount} ₽`,
      });
    } catch (e) {
      setPromoPreview(null);
      notifications.show({ color: 'red', message: apiMessage(e) });
    }
  }

  async function createRegenOrder() {
    setBusy(true);
    try {
      const { data } = await api.post<{
        task_uuid: string;
        category: string;
        tier: string;
        company_id?: number;
      }>(`/models/${uuid}/regenerate`);
      const { data: order } = await api.post<{
        id: number;
        status: string;
        amount?: number;
        balance?: number;
      }>('/orders/create', {
        task_uuid: data.task_uuid,
        category: data.category,
        tier: data.tier,
        company_id: data.company_id,
        promocode: promocode.trim() || undefined,
      });
      if (typeof order.balance === 'number') setBalance(order.balance);
      closeRegen();
      setPromocode('');
      setPromoPreview(null);
      if (order.status === 'awaiting_payment') {
        const shortage = Math.max(payAmount - (order.balance ?? balance ?? 0), 0);
        setTopupShortage(shortage || payAmount);
        setTopupAmount(Math.max(shortage || payAmount, 100));
        openTopup();
        notifications.show({
          color: 'orange',
          message: `Недостаточно средств. Пополните баланс на ${(shortage || payAmount).toLocaleString('ru-RU')} ₽`,
        });
        return;
      }
      notifications.show({ color: 'teal', message: `Заказ #${order.id} в очереди` });
      router.push(`/orders/${order.id}`);
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function payRegen() {
    const currentBalance = balance ?? 0;
    if (currentBalance < payAmount) {
      const shortage = payAmount - currentBalance;
      setTopupShortage(shortage);
      setTopupAmount(Math.max(shortage, 100));
      openTopup();
      return;
    }
    await createRegenOrder();
  }

  async function topup(method: 'redirect' | 'sbp_qr') {
    const value = typeof topupAmount === 'number' ? topupAmount : Number(topupAmount);
    if (!value || value < 100) {
      notifications.show({ color: 'red', message: 'Минимум 100 ₽' });
      return;
    }
    setPaying(true);
    try {
      const { data } = await api.post<{
        confirmation_url?: string;
        status?: string;
        dev_mock?: boolean;
        balance?: number;
      }>('/user/balance/topup', { amount: value, payment_method: method });
      if (data.confirmation_url) {
        window.location.href = data.confirmation_url;
        return;
      }
      if (data.dev_mock || data.status === 'succeeded') {
        if (typeof data.balance === 'number') setBalance(data.balance);
        notifications.show({ color: 'green', message: 'Баланс пополнен' });
        closeTopup();
        return;
      }
      notifications.show({ color: 'yellow', message: 'Нет данных оплаты от платёжной системы' });
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e, 'Не удалось создать платёж') });
    } finally {
      setPaying(false);
    }
  }

  async function submitRate() {
    setBusy(true);
    try {
      await api.post(`/models/${uuid}/rate`, { rating: Number(rating), reasons: [] });
      notifications.show({ color: 'teal', message: 'Спасибо за оценку!' });
      closeRate();
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  function resetRegenModal() {
    closeRegen();
    setPromocode('');
    setPromoPreview(null);
    setRegenMode('3');
  }

  return (
    <div className={styles.root}>
      <div className={styles.viewer}>
        {loading ? (
          <div className={styles.loaderWrap}>
            <Loader color="brand" />
          </div>
        ) : url ? (
          <ModelViewer3D
            src={url}
            height="100%"
            autoRotate
            background={BEIGE}
            borderRadius={0}
          />
        ) : (
          <div className={styles.errorWrap}>{err || 'GLB недоступен'}</div>
        )}
      </div>

      <header className={styles.overlayTop}>
        <Button
          className={`${styles.backBtn} ${styles.actionBtn}`}
          variant="default"
          size="compact-sm"
          leftSection={<IconArrowLeft size={16} />}
          onClick={() => router.back()}
        >
          Назад
        </Button>

        <div className={styles.titleBlock}>
          <div className={styles.titleMain}>3DVektor · интерактивный просмотр</div>
          <div className={styles.titleSub}>Название: {displayName}</div>
        </div>

        <div className={styles.actions}>
          <Menu shadow="md" width={280} position="bottom-end" withinPortal>
            <Menu.Target>
              <Button
                className={styles.actionBtn}
                variant="default"
                size="compact-sm"
                leftSection={<IconDownload size={16} />}
                loading={busy}
              >
                Скачать
              </Button>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Label>Wildberries</Menu.Label>
              <Menu.Item onClick={() => void download('glb')}>GLB</Menu.Item>
              <Menu.Item onClick={() => void download('usdz')}>USDZ</Menu.Item>
              <Menu.Divider />
              <Menu.Label>OZON</Menu.Label>
              <Menu.Item onClick={() => void download('glb')}>GLB</Menu.Item>
              <Menu.Item onClick={() => void download('gltf')}>GLTF</Menu.Item>
              <Menu.Divider />
              <Menu.Label>Объёмная визуализация (Volumetric)</Menu.Label>
              <Menu.Item onClick={() => void download('ply')}>PLY (3D Gaussian Splatting)</Menu.Item>
              <Menu.Divider />
              <Menu.Label>Печать на 3D-принтере</Menu.Label>
              <Menu.Item onClick={() => void download('stl')}>STL (Stereolithography)</Menu.Item>
              <Menu.Divider />
              <Menu.Label>Другие форматы</Menu.Label>
              <Menu.Item onClick={() => void download('usd')}>USD</Menu.Item>
              <Menu.Item onClick={() => void download('usda')}>USDA</Menu.Item>
              <Menu.Item onClick={() => void download('usdc')}>USDC</Menu.Item>
            </Menu.Dropdown>
          </Menu>

          <Button
            className={styles.actionBtn}
            variant="default"
            size="compact-sm"
            leftSection={<IconStar size={16} />}
            onClick={openRate}
          >
            Оцените результат
          </Button>

          <Button
            className={styles.actionBtn}
            component={Link}
            href="/orders/new"
            variant="default"
            size="compact-sm"
            leftSection={<IconSparkles size={16} />}
          >
            Сгенерировать новый 3D объект
          </Button>

          <Tooltip
            multiline
            w={280}
            label="Чтобы при перегенерации ваш объект выглядел лучше, загрузите более качественные фотографии: попробуйте изменить освещение или сделать снимки на другом фоне."
          >
            <Button
              className={styles.actionBtn}
              variant="default"
              size="compact-sm"
              leftSection={<IconRefresh size={16} />}
              onClick={openRegen}
            >
              Перегенерировать
            </Button>
          </Tooltip>
        </div>
      </header>

      <Modal opened={rateOpen} onClose={closeRate} title="Оцените результат" centered radius="lg">
        <Stack>
          <Text size="sm" c="dimmed">
            Поставьте оценку от 1 до 5 звёзд
          </Text>
          <Radio.Group value={rating} onChange={setRating}>
            <Group>
              {['1', '2', '3', '4', '5'].map((v) => (
                <Radio key={v} value={v} label={`${v} ★`} />
              ))}
            </Group>
          </Radio.Group>
          <Button loading={busy} onClick={() => void submitRate()}>
            Отправить оценку
          </Button>
        </Stack>
      </Modal>

      <Modal
        opened={regenOpen}
        onClose={resetRegenModal}
        title="Перегенерация 3D-объекта"
        centered
        radius="lg"
        size="lg"
      >
        <Stack>
          <Text size="sm" fw={600}>
            Выберите вариант перегенерации
          </Text>
          <Radio.Group value={regenMode} onChange={setRegenMode}>
            <Stack gap="sm">
              {REGEN_MODES.map((mode) => (
                <Radio key={mode.value} value={mode.value} label={mode.label} />
              ))}
            </Stack>
          </Radio.Group>
          <Text size="sm" c="dimmed">
            {regenHint}
          </Text>

          <Divider />

          <Group justify="space-between">
            <Text size="sm">К оплате</Text>
            <Text fw={700}>{payAmount.toLocaleString('ru-RU')} ₽</Text>
          </Group>
          {balance != null && (
            <Text size="xs" c="dimmed">
              Баланс: {balance.toLocaleString('ru-RU')} ₽
              {balance < payAmount
                ? ` · не хватает ${(payAmount - balance).toLocaleString('ru-RU')} ₽`
                : ''}
            </Text>
          )}

          <TextInput
            label="Промокод"
            placeholder="Введите промокод"
            value={promocode}
            onChange={(e) => setPromocode(e.currentTarget.value.toUpperCase())}
          />
          <Group>
            <Button variant="light" disabled={!promocode.trim()} onClick={() => void validatePromo()}>
              Ввести промокод
            </Button>
          </Group>
          {promoPreview && (
            <Text size="sm" c="teal">
              Скидка {promoPreview.discount_amount} ₽ · итого {promoPreview.final_amount} ₽
            </Text>
          )}

          <Button loading={busy} onClick={() => void payRegen()}>
            Оплатить {payAmount.toLocaleString('ru-RU')} ₽
          </Button>
        </Stack>
      </Modal>

      <Modal opened={topupOpen} onClose={closeTopup} title="Пополнение баланса" centered radius="lg">
        <Stack>
          <Text size="sm">
            Недостаёт{' '}
            <Text span fw={700} c="orange">
              {topupShortage.toLocaleString('ru-RU')} ₽
            </Text>{' '}
            для оплаты перегенерации
          </Text>
          <TextInput
            label="Сумма пополнения"
            type="number"
            min={100}
            value={topupAmount}
            onChange={(e) => setTopupAmount(e.currentTarget.value)}
          />
          <Button loading={paying} onClick={() => void topup('redirect')}>
            Оплатить картой
          </Button>
          <Button variant="light" loading={paying} onClick={() => void topup('sbp_qr')}>
            СБП (QR)
          </Button>
          <Button component={Link} href="/balance" variant="subtle" size="xs">
            Перейти в раздел «Баланс»
          </Button>
        </Stack>
      </Modal>
    </div>
  );
}
