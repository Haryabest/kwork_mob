import {
  Alert,
  Badge,
  Button,
  Card,
  Center,
  Code,
  Group,
  Loader,
  ScrollArea,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { IconPlayerPlay, IconRefresh, IconDeviceFloppy } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { useCallback, useEffect, useState } from 'react';
import { PageHeader, StateBadge } from '../components/Panel';
import { api, getApiError } from '../services/api';

type WorkerConfig = {
  container_name: string;
  docker_image: string;
  worker_repo_path: string;
  hf_cache_host_path: string;
  state_volume: string;
  extra_hosts: string;
  deploy_enabled: boolean;
  deploy_root: string;
  compose_file: string;
  env_file: string;
  docker_available: boolean;
  docker_status?: { available?: boolean; reason?: string; hint?: string };
  updated_at?: string | null;
  applied_at?: string | null;
  last_apply_ok?: boolean | null;
  env: Record<string, string>;
};

type VerifyResult = {
  ok: boolean;
  message?: string;
  container?: string;
  status?: { running?: boolean; status?: string; image?: string };
  mismatches?: Array<{ key: string; expected: string; actual: string }>;
  applied_at?: string | null;
  last_apply_ok?: boolean | null;
};

const MASK = '••••••••';

type EnvPreset = {
  id: string;
  title: string;
  description: string;
  env: Record<string, string>;
};

const ENV_FIELDS: { key: string; label: string; secret?: boolean }[] = [
  { key: 'WORKER_ID', label: 'WORKER_ID' },
  { key: 'WORKER_TOKEN', label: 'WORKER_TOKEN', secret: true },
  { key: 'WORKER_PIPELINE_MODE', label: 'WORKER_PIPELINE_MODE' },
  { key: 'TRELLIS_VERSION', label: 'TRELLIS_VERSION' },
  { key: 'TRELLIS_ALLOW_STUB_FALLBACK', label: 'TRELLIS_ALLOW_STUB_FALLBACK' },
  { key: 'TRELLIS2_PIPELINE_TYPE', label: 'TRELLIS2_PIPELINE_TYPE' },
  { key: 'TRELLIS2_TEXTURE_SIZE', label: 'TRELLIS2_TEXTURE_SIZE' },
  { key: 'TRELLIS2_DECIMATION', label: 'TRELLIS2_DECIMATION' },
  { key: 'TRELLIS2_LOW_VRAM', label: 'TRELLIS2_LOW_VRAM' },
  { key: 'TRELLIS2_EXTENSION_WEBP', label: 'TRELLIS2_EXTENSION_WEBP' },
  { key: 'TRELLIS2_SS_STEPS', label: 'TRELLIS2_SS_STEPS' },
  { key: 'TRELLIS2_SS_GUIDANCE', label: 'TRELLIS2_SS_GUIDANCE' },
  { key: 'TRELLIS2_SS_GUIDANCE_RESCALE', label: 'TRELLIS2_SS_GUIDANCE_RESCALE' },
  { key: 'TRELLIS2_SS_RESCALE_T', label: 'TRELLIS2_SS_RESCALE_T' },
  { key: 'TRELLIS2_SHAPE_STEPS', label: 'TRELLIS2_SHAPE_STEPS' },
  { key: 'TRELLIS2_SHAPE_GUIDANCE', label: 'TRELLIS2_SHAPE_GUIDANCE' },
  { key: 'TRELLIS2_SHAPE_GUIDANCE_RESCALE', label: 'TRELLIS2_SHAPE_GUIDANCE_RESCALE' },
  { key: 'TRELLIS2_SHAPE_RESCALE_T', label: 'TRELLIS2_SHAPE_RESCALE_T' },
  { key: 'TRELLIS2_TEX_STEPS', label: 'TRELLIS2_TEX_STEPS' },
  { key: 'TRELLIS2_TEX_GUIDANCE', label: 'TRELLIS2_TEX_GUIDANCE' },
  { key: 'TRELLIS2_TEX_GUIDANCE_RESCALE', label: 'TRELLIS2_TEX_GUIDANCE_RESCALE' },
  { key: 'TRELLIS2_TEX_RESCALE_T', label: 'TRELLIS2_TEX_RESCALE_T' },
  { key: 'WORKER_TRELLIS_INPROCESS', label: 'WORKER_TRELLIS_INPROCESS' },
  { key: 'WORKER_WARMUP_TRELLIS', label: 'WORKER_WARMUP_TRELLIS' },
  { key: 'WORKER_STARTUP_WARMUP', label: 'WORKER_STARTUP_WARMUP' },
  { key: 'TRELLIS_SKIP_INTERNAL_REMBG', label: 'TRELLIS_SKIP_INTERNAL_REMBG' },
  { key: 'ATTN_BACKEND', label: 'ATTN_BACKEND (sparse: xformers)' },
  { key: 'SPARSE_ATTN_BACKEND', label: 'SPARSE_ATTN_BACKEND' },
  { key: 'PYTORCH_CUDA_ALLOC_CONF', label: 'PYTORCH_CUDA_ALLOC_CONF' },
  { key: 'NOBG_ENGINE', label: 'NOBG_ENGINE' },
  { key: 'NOBG_MODEL_ID', label: 'NOBG_MODEL_ID (RMBG-2.0)' },
  { key: 'NOBG_VIEW00_ONLY', label: 'NOBG_VIEW00_ONLY' },
  { key: 'NOBG_INPUT_SIZE', label: 'NOBG_INPUT_SIZE (1024)' },
  { key: 'NOBG_SENSITIVITY', label: 'NOBG_SENSITIVITY (1.0)' },
  { key: 'NOBG_MASK_BLUR', label: 'NOBG_MASK_BLUR' },
  { key: 'NOBG_MASK_OFFSET', label: 'NOBG_MASK_OFFSET' },
  { key: 'NOBG_INVERT_OUTPUT', label: 'NOBG_INVERT_OUTPUT' },
  { key: 'NOBG_REFINE_FOREGROUND', label: 'NOBG_REFINE_FOREGROUND' },
  { key: 'NOBG_CONFIDENCE', label: 'NOBG_CONFIDENCE' },
  { key: 'NOBG_HARD_FAIL_MIN', label: 'NOBG_HARD_FAIL_MIN' },
  { key: 'TRELLIS2_SS_GUIDANCE_INTERVAL_START', label: 'TRELLIS2_SS_GUIDANCE_INTERVAL_START' },
  { key: 'TRELLIS2_SS_GUIDANCE_INTERVAL_END', label: 'TRELLIS2_SS_GUIDANCE_INTERVAL_END' },
  { key: 'TRELLIS2_SHAPE_GUIDANCE_INTERVAL_START', label: 'TRELLIS2_SHAPE_GUIDANCE_INTERVAL_START' },
  { key: 'TRELLIS2_SHAPE_GUIDANCE_INTERVAL_END', label: 'TRELLIS2_SHAPE_GUIDANCE_INTERVAL_END' },
  { key: 'TRELLIS2_TEX_GUIDANCE_INTERVAL_START', label: 'TRELLIS2_TEX_GUIDANCE_INTERVAL_START' },
  { key: 'TRELLIS2_TEX_GUIDANCE_INTERVAL_END', label: 'TRELLIS2_TEX_GUIDANCE_INTERVAL_END' },
  { key: 'TRELLIS2_MAX_VIEWS', label: 'TRELLIS2_MAX_VIEWS' },
  { key: 'TRELLIS2_SS_RESOLUTION', label: 'TRELLIS2_SS_RESOLUTION' },
  { key: 'TRELLIS2_SAMPLER', label: 'TRELLIS2_SAMPLER (euler)' },
  { key: 'TRELLIS2_FILL_HOLES', label: 'TRELLIS2_FILL_HOLES' },
  { key: 'TRELLIS2_HOLE_ITERATIONS', label: 'TRELLIS2_HOLE_ITERATIONS' },
  { key: 'TRELLIS2_USE_TILED_DECODER', label: 'TRELLIS2_USE_TILED_DECODER' },
  { key: 'TRELLIS2_GENERATE_TEXTURE_SLAT', label: 'TRELLIS2_GENERATE_TEXTURE_SLAT' },
  { key: 'QUALITY_THRESHOLD', label: 'QUALITY_THRESHOLD (0.3–0.45, не 1.0)' },
  { key: 'TRELLIS_STAGED_PIPELINE', label: 'TRELLIS_STAGED_PIPELINE' },
  { key: 'TRELLIS2_REFINE_SHAPE', label: 'TRELLIS2_REFINE_SHAPE' },
  { key: 'TRELLIS2_SHAPE_REFINE_STEPS', label: 'TRELLIS2_SHAPE_REFINE_STEPS' },
  { key: 'TRELLIS2_SHAPE_REFINE_GUIDANCE', label: 'TRELLIS2_SHAPE_REFINE_GUIDANCE' },
  { key: 'TRELLIS2_SHAPE_REFINE_GUIDANCE_RESCALE', label: 'TRELLIS2_SHAPE_REFINE_GUIDANCE_RESCALE' },
  { key: 'TRELLIS2_SHAPE_REFINE_RESCALE_T', label: 'TRELLIS2_SHAPE_REFINE_RESCALE_T' },
  { key: 'TRELLIS2_SHAPE_REFINE_GUIDANCE_INTERVAL_START', label: 'TRELLIS2_SHAPE_REFINE_INTERVAL_START' },
  { key: 'TRELLIS2_SHAPE_REFINE_GUIDANCE_INTERVAL_END', label: 'TRELLIS2_SHAPE_REFINE_INTERVAL_END' },
  { key: 'TRELLIS2_DOWNSAMPLING', label: 'TRELLIS2_DOWNSAMPLING' },
  { key: 'TRELLIS2_MAX_NUM_TOKENS', label: 'TRELLIS2_MAX_NUM_TOKENS' },
  { key: 'TRELLIS2_REMESH', label: 'TRELLIS2_REMESH' },
  { key: 'TRELLIS2_REMESH_PROJECT', label: 'TRELLIS2_REMESH_PROJECT' },
  { key: 'TRELLIS2_RECONSTRUCT_RESOLUTION', label: 'TRELLIS2_RECONSTRUCT_RESOLUTION' },
  { key: 'TRELLIS2_DUAL_CONTOURING_RESOLUTION', label: 'TRELLIS2_DUAL_CONTURING_RESOLUTION' },
  { key: 'TRELLIS2_REMOVE_FLOATERS', label: 'TRELLIS2_REMOVE_FLOATERS' },
  { key: 'TRELLIS2_REMOVE_INNER_FACES', label: 'TRELLIS2_REMOVE_INNER_FACES' },
  { key: 'TRELLIS2_SIMPLIFY_TARGET_FACES', label: 'TRELLIS2_SIMPLIFY_TARGET_FACES (1M)' },
  { key: 'TRELLIS2_SIMPLIFY_METHOD', label: 'TRELLIS2_SIMPLIFY_METHOD (cumesh)' },
  { key: 'TRELLIS2_REORIENT_VERTICES', label: 'TRELLIS2_REORIENT_VERTICES (90)' },
  { key: 'TRELLIS2_SMOOTH_NORMALS', label: 'TRELLIS2_SMOOTH_NORMALS' },
  { key: 'TRELLIS2_DECIMATION', label: 'TRELLIS2_DECIMATION' },
  { key: 'TRELLIS2_REMESH_BAND', label: 'TRELLIS2_REMESH_BAND' },
  { key: 'TRELLIS2_EXPORT_TEXTURE_MAX', label: 'TRELLIS2_EXPORT_TEXTURE_MAX' },
  { key: 'SEGMENTATION_AVG_MIN', label: 'SEGMENTATION_AVG_MIN' },
  { key: 'COMPRESS_ALLOW_OVER_LIMIT', label: 'COMPRESS_ALLOW_OVER_LIMIT' },
  { key: 'WORKER_SUBPROCESS_STREAM', label: 'WORKER_SUBPROCESS_STREAM' },
  { key: 'WATERMARK_HMAC_SECRET', label: 'WATERMARK_HMAC_SECRET', secret: true },
  { key: 'HF_TOKEN', label: 'HF_TOKEN', secret: true },
  { key: 'ORCHESTRATOR_WS_URL', label: 'ORCHESTRATOR_WS_URL' },
  { key: 'ORCHESTRATOR_HTTP_URL', label: 'ORCHESTRATOR_HTTP_URL' },
  { key: 'REDIS_URL', label: 'REDIS_URL' },
  { key: 'MINIO_ENDPOINT', label: 'MINIO_ENDPOINT' },
  { key: 'MINIO_ACCESS_KEY', label: 'MINIO_ACCESS_KEY', secret: true },
  { key: 'MINIO_SECRET_KEY', label: 'MINIO_SECRET_KEY', secret: true },
];

export default function TrellisSettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [applying, setApplying] = useState(false);
  const [cfg, setCfg] = useState<WorkerConfig | null>(null);
  const [env, setEnv] = useState<Record<string, string>>({});
  const [meta, setMeta] = useState({
    container_name: 'kwork-worker',
    docker_image: '',
    worker_repo_path: '',
    hf_cache_host_path: '',
    state_volume: 'kwork_worker_state',
    extra_hosts: 'host.docker.internal:host-gateway',
  });
  const [verify, setVerify] = useState<VerifyResult | null>(null);
  const [logs, setLogs] = useState('');
  const [logsLoading, setLogsLoading] = useState(false);
  const [presets, setPresets] = useState<Record<string, EnvPreset>>({});

  const load = useCallback(async () => {
    const [{ data }, { data: presetData }] = await Promise.all([
      api.get<WorkerConfig>('/admin/trellis/worker-config'),
      api.get<Record<string, EnvPreset>>('/admin/trellis/worker-config/presets'),
    ]);
    setCfg(data);
    setPresets(presetData || {});
    setMeta({
      container_name: data.container_name,
      docker_image: data.docker_image,
      worker_repo_path: data.worker_repo_path,
      hf_cache_host_path: data.hf_cache_host_path,
      state_volume: data.state_volume,
      extra_hosts: data.extra_hosts,
    });
    setEnv(data.env || {});
  }, []);

  const loadVerify = useCallback(async () => {
    const { data } = await api.get<VerifyResult>('/admin/trellis/worker-config/verify');
    setVerify(data);
  }, []);

  const loadLogs = useCallback(async () => {
    setLogsLoading(true);
    try {
      const { data } = await api.get<{ raw?: string; ok?: boolean; items?: Array<{ message: string }> }>(
        '/admin/trellis/worker-config/logs',
        { params: { tail: 400 } },
      );
      const text = data.raw || (data.items || []).map((i) => i.message).join('\n');
      setLogs(text || (data.ok === false ? 'Логи пусты или контейнер не запущен' : ''));
    } catch (e) {
      setLogs(getApiError(e));
    } finally {
      setLogsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load()
      .then(() => loadVerify())
      .catch((e) => notifications.show({ color: 'red', message: getApiError(e) }))
      .finally(() => setLoading(false));
  }, [load, loadVerify]);

  function setEnvField(key: string, value: string) {
    setEnv((prev) => ({ ...prev, [key]: value }));
  }

  function applyPreset(id: string) {
    const preset = presets[id];
    if (!preset?.env) return;
    setEnv((prev) => {
      const next = { ...prev };
      for (const { key, secret } of ENV_FIELDS) {
        const val = preset.env[key];
        if (val === undefined) continue;
        if (secret && (prev[key] === MASK || !prev[key])) continue;
        next[key] = val;
      }
      return next;
    });
    notifications.show({ color: 'blue', message: `Пресет «${preset.title}» подставлен в форму` });
  }

  async function save() {
    setSaving(true);
    try {
      const payload = {
        ...meta,
        env: Object.fromEntries(
          ENV_FIELDS.map(({ key }) => [key, env[key] ?? '']).filter(([, v]) => v !== MASK),
        ),
      };
      const { data } = await api.put<WorkerConfig>('/admin/trellis/worker-config', payload);
      setCfg(data);
      setEnv(data.env);
      notifications.show({ color: 'teal', message: 'Настройки сохранены' });
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setSaving(false);
    }
  }

  async function apply() {
    setApplying(true);
    try {
      await save();
      const { data } = await api.post<{
        ok: boolean;
        message?: string;
        verify?: VerifyResult;
      }>('/admin/trellis/worker-config/apply');
      setVerify(data.verify || null);
      notifications.show({
        color: data.ok ? 'teal' : 'red',
        message: data.ok ? 'Контейнер перезапущен' : (data.message?.slice(0, 400) || 'Ошибка apply'),
      });
      await load();
      await loadVerify();
      await loadLogs();
    } catch (e) {
      notifications.show({ color: 'red', message: getApiError(e) });
    } finally {
      setApplying(false);
    }
  }

  if (loading || !cfg) {
    return (
      <Center py="xl">
        <Loader color="brand" />
      </Center>
    );
  }

  return (
    <>
      <PageHeader
        title="Настройка TRELLIS"
        description="GPU-воркер: переменные docker run, apply и логи контейнера"
        action={
          <Group>
            <Button variant="light" leftSection={<IconRefresh size={16} />} onClick={() => void loadVerify()}>
              Проверить
            </Button>
            <Button variant="default" leftSection={<IconDeviceFloppy size={16} />} loading={saving} onClick={() => void save()}>
              Сохранить
            </Button>
            <Button
              leftSection={<IconPlayerPlay size={16} />}
              loading={applying}
              disabled={!cfg.deploy_enabled}
              onClick={() => void apply()}
            >
              Применить и перезапустить
            </Button>
          </Group>
        }
      />

      {!cfg.deploy_enabled && (
        <Alert color="orange" mb="md" title="Docker deploy отключён">
          Задайте <Code>WORKER_DEPLOY_ENABLED=1</Code> в <Code>.env</Code>, пересоберите orchestrator. Нужны{' '}
          <Code>/var/run/docker.sock</Code> и <Code>WORKER_DEPLOY_ROOT=/repo</Code>.
        </Alert>
      )}
      {cfg.deploy_enabled && !cfg.docker_available && cfg.docker_status?.hint && (
        <Alert color="red" mb="md" title="Docker недоступен">
          {cfg.docker_status.hint}
        </Alert>
      )}

      <SimpleGrid cols={{ base: 1, md: 2 }} mb="md">
        <Card withBorder>
          <Stack gap="sm">
            <Title order={5}>Статус</Title>
            <Group gap="xs">
              <StateBadge
                value={cfg.docker_available ? 'docker ok' : 'docker недоступен'}
                color={cfg.docker_available ? 'teal' : 'red'}
              />
              <StateBadge
                value={verify?.ok ? 'настройки совпадают' : 'есть расхождения'}
                color={verify?.ok ? 'teal' : 'orange'}
              />
              {verify?.status?.running && <Badge color="green">контейнер running</Badge>}
            </Group>
            <Text size="xs" c="dimmed">
              Корень: {cfg.deploy_root}
            </Text>
            <Text size="xs" c="dimmed">
              Compose: {cfg.compose_file}
            </Text>
            {cfg.updated_at && (
              <Text size="xs" c="dimmed">
                Сохранено: {new Date(cfg.updated_at).toLocaleString('ru-RU')}
              </Text>
            )}
            {cfg.applied_at && (
              <Text size="xs" c="dimmed">
                Применено: {new Date(cfg.applied_at).toLocaleString('ru-RU')}
                {cfg.last_apply_ok === false ? ' (ошибка)' : ''}
              </Text>
            )}
            {verify?.mismatches && verify.mismatches.length > 0 && (
              <Stack gap={4}>
                <Text size="sm" fw={600} c="orange">
                  Расхождения:
                </Text>
                {verify.mismatches.map((m) => (
                  <Text key={m.key} size="xs" c="dimmed">
                    {m.key}
                  </Text>
                ))}
              </Stack>
            )}
          </Stack>
        </Card>

        <Card withBorder>
          <Stack gap="sm">
            <Title order={5}>Docker</Title>
            <TextInput
              label="Имя контейнера"
              value={meta.container_name}
              onChange={(e) => setMeta({ ...meta, container_name: e.currentTarget.value })}
            />
            <TextInput
              label="Образ"
              value={meta.docker_image}
              onChange={(e) => setMeta({ ...meta, docker_image: e.currentTarget.value })}
            />
            <TextInput
              label="Путь к worker/ на хосте"
              value={meta.worker_repo_path}
              onChange={(e) => setMeta({ ...meta, worker_repo_path: e.currentTarget.value })}
            />
            <TextInput
              label="HF cache на хосте"
              value={meta.hf_cache_host_path}
              onChange={(e) => setMeta({ ...meta, hf_cache_host_path: e.currentTarget.value })}
            />
            <TextInput
              label="Volume state"
              value={meta.state_volume}
              onChange={(e) => setMeta({ ...meta, state_volume: e.currentTarget.value })}
            />
          </Stack>
        </Card>
      </SimpleGrid>

      <Card withBorder mb="md">
        <Group justify="space-between" mb="sm">
          <Title order={5}>Переменные окружения (-e)</Title>
          <Group gap="xs">
            {Object.values(presets).map((p) => (
              <Button key={p.id} size="xs" variant="light" onClick={() => applyPreset(p.id)}>
                {p.title}
              </Button>
            ))}
          </Group>
        </Group>
        {Object.values(presets).length > 0 && (
          <Text size="xs" c="dimmed" mb="sm">
            {Object.values(presets)
              .map((p) => `${p.title}: ${p.description}`)
              .join(' · ')}
          </Text>
        )}
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
          {ENV_FIELDS.map(({ key, label, secret }) => (
            <TextInput
              key={key}
              label={label}
              type={secret ? 'password' : 'text'}
              value={env[key] ?? ''}
              placeholder={secret ? 'оставьте пустым, чтобы не менять' : ''}
              onChange={(e) => setEnvField(key, e.currentTarget.value)}
            />
          ))}
        </SimpleGrid>
      </Card>

      <Card withBorder>
        <Group justify="space-between" mb="sm">
          <Title order={5}>Логи контейнера</Title>
          <Button size="xs" variant="light" loading={logsLoading} onClick={() => void loadLogs()}>
            Обновить
          </Button>
        </Group>
        <ScrollArea h={320}>
          <Code block style={{ whiteSpace: 'pre-wrap', fontSize: 11 }}>
            {logs || 'Нажмите «Обновить» для загрузки docker logs'}
          </Code>
        </ScrollArea>
      </Card>
    </>
  );
}
