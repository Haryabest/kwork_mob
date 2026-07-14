import { Badge, Button, Checkbox, Group, Progress, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconChecklist, IconDatabase, IconRefresh, IconTrash } from '@tabler/icons-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, getApiError } from '../services/api';

type CheckItem = { id: string; section: string; label: string };

type SmartSnap = {
  ok?: boolean;
  used_percent?: number | null;
  free_percent?: number | null;
  smart?: { status?: string; note?: string };
  smart_disks?: Array<{
    device?: string;
    health?: string;
    temp_c?: number;
    reallocated_sectors?: number;
    wear_percent?: number;
    remaining_life_percent?: number;
  }>;
  alert_disk_critical?: boolean;
};

export default function MaintenancePage() {
  const [items, setItems] = useState<CheckItem[]>([]);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [smart, setSmart] = useState<SmartSnap | null>(null);
  const [saving, setSaving] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  const loadChecklist = useCallback(async () => {
    const { data } = await api.get<{ items: CheckItem[]; checks: Record<string, boolean> }>(
      '/admin/maintenance/checklist',
    );
    setItems(data.items || []);
    setChecked(data.checks || {});
  }, []);

  const loadSmart = useCallback(async () => {
    try {
      const { data } = await api.get<SmartSnap>('/storage/smart');
      setSmart(data);
    } catch {
      try {
        const { data } = await api.get<SmartSnap>('/storage/health');
        setSmart(data);
      } catch (e) {
        notifications.show({ color: 'yellow', message: getApiError(e) });
      }
    }
  }, []);

  useEffect(() => {
    void loadChecklist().catch((e) => notifications.show({ color: 'red', message: getApiError(e) }));
    void loadSmart();
  }, [loadChecklist, loadSmart]);

  async function toggle(id: string) {
    const next = { ...checked, [id]: !checked[id] };
    setChecked(next);
    setSaving(true);
    try {
      const { data } = await api.put<{ checks: Record<string, boolean> }>('/admin/maintenance/checklist', {
        checks: next,
      });
      setChecked(data.checks || next);
    } catch (e) {
      setChecked(checked);
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setSaving(false);
    }
  }

  const done = useMemo(() => Object.values(checked).filter(Boolean).length, [checked]);
  const sections = useMemo(() => [...new Set(items.map((i) => i.section))], [items]);
  const pct = items.length ? Math.round((done / items.length) * 100) : 0;

  return (
    <div className="vz-page">
      <div className="vz-page-header">
        <div>
          <Title order={2}>Обслуживание</Title>
          <Text c="#6d6c77" size="sm" mt={6}>
            SMART · очистка логов · тест бэкапа §23.7 · {done}/{items.length}
            {saving ? ' · saving…' : ''}
          </Text>
        </div>
        <Group>
          <Button leftSection={<IconRefresh size={16} />} variant="light" onClick={() => void loadSmart()}>
            SMART
          </Button>
          <Button
            leftSection={<IconTrash size={16} />}
            variant="light"
            color="orange"
            loading={busy === 'logs'}
            onClick={async () => {
              setBusy('logs');
              try {
                const { data } = await api.post<{ deleted?: number; older_than_days?: number }>(
                  '/admin/maintenance/cleanup-logs',
                );
                notifications.show({
                  color: 'teal',
                  message: `Логи: удалено ${data.deleted ?? 0} (старше ${data.older_than_days}д)`,
                });
                const next = { ...checked, logs_cleanup: true };
                setChecked(next);
                await api.put('/admin/maintenance/checklist', { checks: next });
              } catch (e) {
                notifications.show({ color: 'red', message: getApiError(e) });
              } finally {
                setBusy(null);
              }
            }}
          >
            Очистить логи
          </Button>
          <Button
            leftSection={<IconDatabase size={16} />}
            variant="light"
            loading={busy === 'backup'}
            onClick={async () => {
              setBusy('backup');
              try {
                const { data } = await api.post<{ mode?: string; result?: { ok?: boolean; error?: string } }>(
                  '/admin/maintenance/backup-restore-test',
                );
                notifications.show({
                  color: data.result?.ok !== false ? 'teal' : 'orange',
                  message: `Backup restore test: ${data.mode} · ${data.result?.error || 'ok'}`,
                });
              } catch (e) {
                notifications.show({ color: 'red', message: getApiError(e) });
              } finally {
                setBusy(null);
              }
            }}
          >
            Тест бэкапа
          </Button>
          <Button component={Link} to="/storage" variant="default" leftSection={<IconChecklist size={16} />}>
            Хранилище
          </Button>
        </Group>
      </div>

      <Progress value={pct} mb="lg" color={pct === 100 ? 'teal' : 'brand'} size="md" />

      <SimpleGrid cols={{ base: 1, md: 2 }} mb="lg">
        <div className="vz-surface">
          <Group justify="space-between" mb="sm">
            <Text fw={600}>S.M.A.R.T. snapshot</Text>
            <Badge color={smart?.alert_disk_critical ? 'red' : smart?.ok ? 'teal' : 'orange'} variant="light">
              {smart?.smart?.status || (smart?.ok ? 'ok' : '—')}
            </Badge>
          </Group>
          <Text size="sm">
            used: {smart?.used_percent != null ? `${smart.used_percent}%` : '—'} · free:{' '}
            {smart?.free_percent != null ? `${smart.free_percent}%` : '—'}
          </Text>
          <Text size="xs" c="dimmed" mt={4}>
            {smart?.smart?.note || 'Данные из /storage/smart'}
          </Text>
          <Stack gap={4} mt="md">
            {(smart?.smart_disks || []).slice(0, 6).map((d, i) => (
              <Text key={d.device || i} size="xs">
                {d.device || 'disk'}: {d.health || '—'}
                {d.temp_c != null ? ` · ${d.temp_c}°C` : ''}
                {d.reallocated_sectors != null ? ` · realloc ${d.reallocated_sectors}` : ''}
                {d.wear_percent != null || d.remaining_life_percent != null
                  ? ` · wear ${d.wear_percent ?? d.remaining_life_percent}%`
                  : ''}
              </Text>
            ))}
            {!smart?.smart_disks?.length && (
              <Text size="xs" c="dimmed">
                Нет SMART disks — настройте MINIO_SMART_JSON
              </Text>
            )}
          </Stack>
        </div>
        <div className="vz-surface">
          <Text fw={600} mb="sm">
            Быстрые действия
          </Text>
          <Text size="sm" c="dimmed" mb="md">
            Force Resync / FIO / Docker logs — на странице Хранилище. Этот чек-лист фиксирует регулярный обход.
          </Text>
          <Button component={Link} to="/storage" variant="light" fullWidth>
            Открыть инструменты §11.16.4
          </Button>
        </div>
      </SimpleGrid>

      <div className="vz-grid vz-grid-2-lg">
        {sections.map((section) => (
          <div key={section} className="vz-surface">
            <Text fw={600} mb="md">
              {section}
            </Text>
            <Stack gap="sm">
              {items
                .filter((i) => i.section === section)
                .map((item) => (
                  <Checkbox
                    key={item.id}
                    label={item.label}
                    checked={!!checked[item.id]}
                    onChange={() => void toggle(item.id)}
                  />
                ))}
            </Stack>
          </div>
        ))}
      </div>
    </div>
  );
}
