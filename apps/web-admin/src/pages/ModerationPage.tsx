import {
  Badge,
  Button,
  Center,
  Group,
  Image,
  Loader,
  Modal,
  Progress,
  Select,
  SimpleGrid,
  Stack,
  Tabs,
  Text,
  TextInput,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconDownload } from '@tabler/icons-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { MetricGrid, PageHeader, ShellTable, StateBadge } from '../components/Panel';
import { api, getApiError } from '../services/api';

type Preview = { index: number; filename: string; label?: string; preview_url: string };

type Report = {
  id: number;
  order_id: number;
  user_id: number;
  user_email?: string;
  user_status?: string;
  reason: string;
  refunded: boolean;
  verified: boolean;
  created_at?: string;
  hours_left?: number;
  hours_overdue?: number;
  overdue?: boolean;
  urgent?: boolean;
  amount?: number;
  order_status?: string;
  task_uuid?: string;
  photo_previews?: Preview[];
};

type SlaDash = {
  pending: number;
  overdue: number;
  urgent: number;
  within_sla: number;
  avg_hours_left?: number | null;
  oldest_pending_hours?: number | null;
  verified_24h: number;
  verified_7d: number;
  sla_met_rate: number;
  sla_ok: boolean;
  sla_hours: number;
  queue?: Report[];
};

type BlackWord = { id: number; word: string; category: string; is_active: boolean };

type AgeEvent = {
  id: number;
  user_id: number | null;
  email?: string | null;
  age?: number;
  success: boolean;
  category?: string;
  created_at?: string | null;
};

type AgeUser = {
  user_id: number;
  email?: string;
  date_of_birth?: string | null;
  age_years?: number | null;
  age_verified_at?: string | null;
  status?: string;
};

function slaLabel(r: Report) {
  if (r.overdue) {
    return (
      <Badge color="red">
        просрочено{r.hours_overdue != null ? ` ${r.hours_overdue}ч` : r.hours_left != null ? ` ${Math.abs(r.hours_left)}ч` : ''}
      </Badge>
    );
  }
  if (r.urgent || (r.hours_left != null && r.hours_left <= 6)) {
    return (
      <Badge color="orange">
        срочно {r.hours_left != null ? `${r.hours_left}ч` : ''}
      </Badge>
    );
  }
  return <Text size="sm">{r.hours_left != null ? `${r.hours_left}ч` : '—'}</Text>;
}

/** §10.8 / §11 — NSFW queue + age-gate viewer + blacklist */
export default function ModerationPage() {
  const [tab, setTab] = useState<string | null>('nsfw');
  const [items, setItems] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [escalating, setEscalating] = useState(false);
  const [sla, setSla] = useState<SlaDash | null>(null);
  const [queueFilter, setQueueFilter] = useState<string | null>('pending');
  const [preview, setPreview] = useState<{ blockId: number; photos: Preview[] } | null>(null);
  const [blacklist, setBlacklist] = useState<BlackWord[]>([]);
  const [newWord, setNewWord] = useState('');
  const [newCat, setNewCat] = useState<string | null>('general');
  const [blOpen, setBlOpen] = useState(false);

  const [ageLoading, setAgeLoading] = useState(false);
  const [ageEvents, setAgeEvents] = useState<AgeEvent[]>([]);
  const [ageUsers, setAgeUsers] = useState<AgeUser[]>([]);
  const [ageSummary, setAgeSummary] = useState<{
    events: number;
    passed: number;
    failed: number;
    verified_users: number;
  } | null>(null);
  const [ageFilter, setAgeFilter] = useState<string | null>('all');

  const load = useCallback(async () => {
    const verifiedParam =
      queueFilter === 'verified' ? true : queueFilter === 'all' ? undefined : false;
    const [reports, slaRes, bl] = await Promise.all([
      api.get<{ items: Report[] }>('/admin/nsfw/reports', {
        params: verifiedParam === undefined ? {} : { verified: verifiedParam },
      }),
      api.get<SlaDash>('/admin/nsfw/sla'),
      api.get<{ items: BlackWord[] }>('/admin/nsfw/blacklist'),
    ]);
    let list = reports.data.items ?? [];
    if (queueFilter === 'overdue') list = list.filter((i) => i.overdue);
    if (queueFilter === 'urgent') {
      list = list.filter((i) => !i.overdue && (i.urgent || (i.hours_left != null && i.hours_left <= 6)));
    }
    list = [...list].sort((a, b) => {
      const ao = a.overdue ? 0 : 1;
      const bo = b.overdue ? 0 : 1;
      if (ao !== bo) return ao - bo;
      return (a.hours_left ?? 99) - (b.hours_left ?? 99);
    });
    setItems(list);
    setSla(slaRes.data);
    setBlacklist(bl.data.items ?? []);
  }, [queueFilter]);

  const loadAge = useCallback(async () => {
    setAgeLoading(true);
    try {
      const params: { success?: boolean } = {};
      if (ageFilter === 'ok') params.success = true;
      if (ageFilter === 'fail') params.success = false;
      const { data } = await api.get<{
        summary: { events: number; passed: number; failed: number; verified_users: number };
        events: AgeEvent[];
        verified_users: AgeUser[];
      }>('/admin/age-verifications', { params });
      setAgeSummary(data.summary);
      setAgeEvents(data.events ?? []);
      setAgeUsers(data.verified_users ?? []);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setAgeLoading(false);
    }
  }, [ageFilter]);

  useEffect(() => {
    load()
      .catch((e) => notifications.show({ color: 'red', message: getApiError(e) }))
      .finally(() => setLoading(false));
  }, [load]);

  useEffect(() => {
    if (tab === 'age') void loadAge();
  }, [tab, loadAge]);

  async function verify(id: number, legal: boolean) {
    setBusyId(id);
    try {
      await api.post(`/admin/nsfw/${id}/verify`, { legal });
      notifications.show({
        color: legal ? 'teal' : 'orange',
        message: legal ? 'Ложное срабатывание — аккаунт разблокирован' : 'Нарушение подтверждено — бан',
      });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setBusyId(null);
    }
  }

  async function escalateNow() {
    setEscalating(true);
    try {
      const { data } = await api.post<{ overdue: number; alerts_sent: number }>('/admin/nsfw/escalate');
      notifications.show({
        color: 'orange',
        message: `Escalate: overdue=${data.overdue}, alerts sent=${data.alerts_sent}`,
      });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setEscalating(false);
    }
  }

  async function openPhotos(r: Report) {
    try {
      if (r.photo_previews?.length) {
        setPreview({ blockId: r.id, photos: r.photo_previews });
        return;
      }
      const { data } = await api.get<{ items: Preview[] }>(`/admin/nsfw/${r.id}/photos`);
      setPreview({ blockId: r.id, photos: data.items ?? [] });
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  async function addWord() {
    try {
      await api.post('/admin/nsfw/blacklist', { word: newWord.trim(), category: newCat || 'general' });
      setNewWord('');
      notifications.show({ color: 'teal', message: 'Слово добавлено' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  async function removeWord(id: number) {
    try {
      await api.delete(`/admin/nsfw/blacklist/${id}`);
      notifications.show({ color: 'teal', message: 'Слово деактивировано' });
      await load();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  async function exportAgeCsv() {
    try {
      const params: { success?: boolean } = {};
      if (ageFilter === 'ok') params.success = true;
      if (ageFilter === 'fail') params.success = false;
      const { data } = await api.get<Blob>('/admin/age-verifications/export', {
        params: { ...params, limit: 5000 },
        responseType: 'blob',
      });
      const url = URL.createObjectURL(data);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'age-verifications.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    }
  }

  const overdue = sla?.overdue ?? items.filter((i) => i.overdue).length;
  const pending = sla?.pending ?? items.length;
  const slaPct = useMemo(() => Math.round((sla?.sla_met_rate ?? 1) * 1000) / 10, [sla]);

  if (loading) {
    return (
      <Center py="xl">
        <Loader color="brand" />
      </Center>
    );
  }

  return (
    <>
      <PageHeader
        title="Модерация"
        description="NSFW SLA 24ч · age-gate 18+ · чёрный список (§10.8 / §11)"
        action={
          <Group gap="xs">
            {tab === 'nsfw' && (
              <>
                <Button variant="default" onClick={() => setBlOpen(true)}>
                  Чёрный список
                </Button>
                <Button
                  color="orange"
                  variant="light"
                  loading={escalating}
                  onClick={() => void escalateNow()}
                  disabled={!overdue}
                >
                  Escalate overdue
                </Button>
              </>
            )}
            {tab === 'age' && (
              <Button
                leftSection={<IconDownload size={16} />}
                variant="default"
                onClick={() => void exportAgeCsv()}
              >
                CSV
              </Button>
            )}
            <Button
              variant="light"
              loading={tab === 'age' ? ageLoading : false}
              onClick={() =>
                tab === 'age'
                  ? void loadAge()
                  : load().catch((e) => notifications.show({ color: 'red', message: getApiError(e) }))
              }
            >
              Обновить
            </Button>
          </Group>
        }
      />

      <Tabs value={tab} onChange={setTab} mb="md">
        <Tabs.List>
          <Tabs.Tab value="nsfw">
            NSFW
            {overdue > 0 ? (
              <Badge ml={6} size="sm" color="red">
                {overdue}
              </Badge>
            ) : null}
          </Tabs.Tab>
          <Tabs.Tab value="age">Проверки возраста</Tabs.Tab>
        </Tabs.List>
      </Tabs>

      {tab === 'nsfw' && (
        <>
          <MetricGrid
            items={[
              { label: 'Ожидают', value: String(pending), color: 'orange' },
              { label: 'Просрочено >24ч', value: String(overdue), color: overdue ? 'red' : 'teal' },
              { label: 'Срочно ≤6ч', value: String(sla?.urgent ?? 0), color: 'orange' },
              {
                label: 'SLA met (sample)',
                value: `${slaPct}%`,
                color: sla?.sla_ok === false ? 'red' : 'teal',
              },
              { label: 'Verified 24ч', value: String(sla?.verified_24h ?? 0) },
              { label: 'Blacklist', value: String(blacklist.length) },
            ]}
          />
          <SimpleGrid cols={{ base: 1, sm: 2 }} mb="md">
            <Stack gap={6}>
              <Group justify="space-between">
                <Text size="sm">Соблюдение SLA 24ч</Text>
                <Text size="sm" c="dimmed">
                  avg left: {sla?.avg_hours_left ?? '—'}ч · oldest: {sla?.oldest_pending_hours ?? '—'}ч
                </Text>
              </Group>
              <Progress
                value={Math.min(100, slaPct)}
                color={slaPct >= 95 ? 'teal' : slaPct >= 80 ? 'orange' : 'red'}
                size="lg"
                radius="sm"
              />
            </Stack>
            <Select
              label="Фильтр очереди"
              data={[
                { value: 'pending', label: 'Непроверенные' },
                { value: 'overdue', label: 'Только просроченные' },
                { value: 'urgent', label: 'Срочные ≤6ч' },
                { value: 'verified', label: 'Проверенные' },
                { value: 'all', label: 'Все' },
              ]}
              value={queueFilter}
              onChange={setQueueFilter}
              allowDeselect={false}
              maw={280}
            />
          </SimpleGrid>
          <ShellTable
            headers={['ID', 'Превью', 'Заказ', 'Пользователь', 'Причина', 'SLA', 'Refund', 'Действия']}
            rows={
              items.length
                ? items.map((r) => [
                    String(r.id),
                    <Group key={`p-${r.id}`} gap={4}>
                      {(r.photo_previews || []).slice(0, 2).map((ph) => (
                        <Image
                          key={ph.index}
                          src={ph.preview_url}
                          w={40}
                          h={40}
                          radius="sm"
                          fit="cover"
                          onClick={() => void openPhotos(r)}
                          style={{ cursor: 'pointer' }}
                        />
                      ))}
                      <Button size="compact-xs" variant="subtle" onClick={() => void openPhotos(r)}>
                        все
                      </Button>
                    </Group>,
                    `#${r.order_id}${r.amount != null ? ` · ${r.amount}₽` : ''}`,
                    <Stack key={`u-${r.id}`} gap={0}>
                      <Text size="sm">{r.user_email ?? r.user_id}</Text>
                      <Text size="xs" c="dimmed">
                        {r.user_status}
                      </Text>
                    </Stack>,
                    r.reason,
                    slaLabel(r),
                    r.refunded ? <StateBadge key={`rf-${r.id}`} value="да" color="teal" /> : 'нет',
                    r.verified ? (
                      <Badge key={`v-${r.id}`} color="gray">
                        verified
                      </Badge>
                    ) : (
                      <Group key={`a-${r.id}`} gap={6}>
                        <Button
                          size="xs"
                          color="teal"
                          loading={busyId === r.id}
                          onClick={() => void verify(r.id, true)}
                        >
                          Легально
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="light"
                          loading={busyId === r.id}
                          onClick={() => void verify(r.id, false)}
                        >
                          Нарушение
                        </Button>
                      </Group>
                    ),
                  ])
                : [['—', '—', 'Очередь пуста', '—', '—', '—', '—', '—']]
            }
          />
        </>
      )}

      {tab === 'age' && (
        <>
          <Group mb="md" justify="space-between">
            <MetricGrid
              items={[
                { label: 'События', value: String(ageSummary?.events ?? 0) },
                { label: 'Успех', value: String(ageSummary?.passed ?? 0), color: 'teal' },
                { label: 'Отказ / <18', value: String(ageSummary?.failed ?? 0), color: 'red' },
                { label: 'Verified users', value: String(ageSummary?.verified_users ?? 0) },
              ]}
            />
            <Select
              data={[
                { value: 'all', label: 'Все' },
                { value: 'ok', label: 'Успешные' },
                { value: 'fail', label: 'Неуспешные' },
              ]}
              value={ageFilter}
              onChange={setAgeFilter}
              w={160}
              allowDeselect={false}
            />
          </Group>
          {ageLoading ? (
            <Center py="xl">
              <Loader color="brand" />
            </Center>
          ) : (
            <>
              <Text fw={600} mb="sm">
                Журнал age_verification
              </Text>
              <ShellTable
                headers={['ID', 'User', 'Email', 'Age', 'Результат', 'Категория', 'Когда']}
                rows={
                  ageEvents.length
                    ? ageEvents.map((e) => [
                        String(e.id),
                        String(e.user_id ?? '—'),
                        e.email || '—',
                        e.age != null ? String(e.age) : '—',
                        e.success ? (
                          <Badge key={`ok-${e.id}`} color="teal">
                            ok
                          </Badge>
                        ) : (
                          <Badge key={`fail-${e.id}`} color="red">
                            fail
                          </Badge>
                        ),
                        e.category || '—',
                        e.created_at ? e.created_at.slice(0, 19).replace('T', ' ') : '—',
                      ])
                    : [['—', '—', 'Нет записей', '—', '—', '—', '—']]
                }
              />
              <Text fw={600} mt="lg" mb="sm">
                Пользователи с age_verified_at
              </Text>
              <ShellTable
                headers={['User', 'Email', 'DOB', 'Возраст', 'Verified at', 'Status']}
                rows={
                  ageUsers.length
                    ? ageUsers.map((u) => [
                        String(u.user_id),
                        u.email || '—',
                        u.date_of_birth || '—',
                        u.age_years != null ? String(u.age_years) : '—',
                        u.age_verified_at ? u.age_verified_at.slice(0, 19).replace('T', ' ') : '—',
                        u.status || '—',
                      ])
                    : [['—', 'Нет verified', '—', '—', '—', '—']]
                }
              />
            </>
          )}
        </>
      )}

      <Modal
        opened={!!preview}
        onClose={() => setPreview(null)}
        title={preview ? `Фото block #${preview.blockId}` : ''}
        size="xl"
      >
        <SimpleGrid cols={{ base: 2, sm: 3, md: 4 }}>
          {(preview?.photos || []).map((ph) => (
            <Stack key={ph.index} gap={4}>
              <Image src={ph.preview_url} radius="md" mah={180} fit="contain" />
              <Text size="xs" c="dimmed" ta="center">
                {ph.label || ph.filename}
              </Text>
            </Stack>
          ))}
        </SimpleGrid>
        {!preview?.photos?.length && <Text c="dimmed">Нет доступных фото в MinIO</Text>}
      </Modal>

      <Modal opened={blOpen} onClose={() => setBlOpen(false)} title="Чёрный список слов" size="lg">
        <Stack>
          <Group align="flex-end">
            <TextInput
              label="Слово / бренд"
              value={newWord}
              onChange={(e) => setNewWord(e.currentTarget.value)}
              style={{ flex: 1 }}
            />
            <Select
              label="Категория"
              value={newCat}
              onChange={setNewCat}
              data={[
                { value: 'general', label: 'general' },
                { value: 'brand', label: 'brand' },
                { value: 'product', label: 'product' },
                { value: 'nsfw', label: 'nsfw' },
              ]}
              w={140}
            />
            <Button onClick={() => void addWord()} disabled={newWord.trim().length < 2}>
              Добавить
            </Button>
          </Group>
          <ShellTable
            headers={['ID', 'Слово', 'Категория', '']}
            rows={blacklist.map((w) => [
              String(w.id),
              w.word,
              w.category,
              <Button key={w.id} size="xs" color="red" variant="light" onClick={() => void removeWord(w.id)}>
                Удалить
              </Button>,
            ])}
          />
        </Stack>
      </Modal>
    </>
  );
}
