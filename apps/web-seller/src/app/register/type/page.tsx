'use client';

import {
  Alert,
  Button,
  Card,
  Checkbox,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { IconBuilding, IconUser } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { useRouter } from 'next/navigation';
import { useCallback, useState } from 'react';
import { AuthPage } from '../../../components/AuthPage';
import { api, apiMessage } from '../../../services/api';

type InnLookup = {
  found: boolean;
  company_name?: string | null;
  kpp?: string | null;
  ogrn?: string | null;
  legal_address?: string | null;
  director_name?: string | null;
};

type Mismatch = { field: string; expected: string; actual: string };

export default function AccountTypePage() {
  const router = useRouter();
  const [selected, setSelected] = useState<'individual' | 'legal'>('individual');
  const [loading, setLoading] = useState(false);
  const [lookupBusy, setLookupBusy] = useState(false);
  const [fullName, setFullName] = useState('');
  const [inn, setInn] = useState('');
  const [sameAddress, setSameAddress] = useState(true);
  const [confirmMismatch, setConfirmMismatch] = useState(false);
  const [mismatches, setMismatches] = useState<Mismatch[]>([]);
  const [legal, setLegal] = useState({
    company_name: '',
    inn: '',
    kpp: '',
    ogrn: '',
    legal_address: '',
    actual_address: '',
    bank_name: '',
    bik: '',
    checking_account: '',
    corr_account: '',
    director_name: '',
    docs_email: '',
  });

  const lookupInn = useCallback(async (value: string) => {
    const digits = value.replace(/\D/g, '');
    if (digits.length !== 10 && digits.length !== 12) return;
    setLookupBusy(true);
    setMismatches([]);
    setConfirmMismatch(false);
    try {
      const { data } = await api.get<InnLookup>('/auth/inn-lookup', { params: { inn: digits } });
      if (!data.found) {
        notifications.show({ color: 'yellow', message: 'ИНН не найден в реестре' });
        return;
      }
      setLegal((prev) => ({
        ...prev,
        inn: digits,
        company_name: data.company_name || prev.company_name,
        kpp: data.kpp || prev.kpp,
        ogrn: data.ogrn || prev.ogrn,
        legal_address: data.legal_address || prev.legal_address,
        director_name: data.director_name || prev.director_name,
      }));
    } catch (e) {
      notifications.show({ color: 'red', message: apiMessage(e) });
    } finally {
      setLookupBusy(false);
    }
  }, []);

  async function submit() {
    try {
      await api.get('/user/me');
    } catch {
      notifications.show({ color: 'red', message: 'Сессия истекла — войдите снова' });
      router.replace('/');
      return;
    }
    setLoading(true);
    try {
      const payload =
        selected === 'individual'
          ? { account_type: 'individual' as const, full_name: fullName || null, inn: inn || null }
          : {
              account_type: 'legal' as const,
              ...legal,
              actual_address: sameAddress ? legal.legal_address : legal.actual_address,
              full_name: legal.director_name || null,
              confirm_mismatch: confirmMismatch,
            };
      await api.post('/auth/account-type', payload);
      router.replace('/dashboard');
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: { mismatches?: Mismatch[]; message?: string } } } };
      const detail = err.response?.data?.detail;
      if (detail?.mismatches?.length) {
        setMismatches(detail.mismatches);
        notifications.show({
          color: 'orange',
          message: detail.message || 'Данные не совпадают с реестром',
        });
        return;
      }
      notifications.show({ color: 'red', message: apiMessage(error) });
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthPage>
      <Paper withBorder shadow="md" radius="lg" p="xl" w="100%" maw={640}>
        <Stack>
          <div>
            <Title order={2}>Тип аккаунта</Title>
            <Text size="sm" c="dimmed">
              Физическое лицо или юридическое лицо / ИП
            </Text>
          </div>
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <Card
              withBorder
              p="md"
              role="button"
              onClick={() => setSelected('individual')}
              style={{
                cursor: 'pointer',
                borderColor: selected === 'individual' ? 'var(--mantine-color-brand-6)' : undefined,
              }}
            >
              <IconUser />
              <Text fw={600} mt="sm">
                Физическое лицо
              </Text>
              <Text size="xs" c="dimmed">
                Самозанятый / селлер
              </Text>
            </Card>
            <Card
              withBorder
              p="md"
              role="button"
              onClick={() => setSelected('legal')}
              style={{
                cursor: 'pointer',
                borderColor: selected === 'legal' ? 'var(--mantine-color-brand-6)' : undefined,
              }}
            >
              <IconBuilding />
              <Text fw={600} mt="sm">
                Юрлицо / ИП
              </Text>
              <Text size="xs" c="dimmed">
                Команда, роли, Owner
              </Text>
            </Card>
          </SimpleGrid>

          {selected === 'individual' && (
            <Stack gap="sm">
              <TextInput
                label="ФИО"
                description="Опционально, рекомендуется для чеков"
                value={fullName}
                onChange={(e) => setFullName(e.currentTarget.value)}
              />
              <TextInput
                label="ИНН"
                description="Опционально"
                value={inn}
                onChange={(e) => setInn(e.currentTarget.value)}
              />
            </Stack>
          )}

          {selected === 'legal' && (
            <Stack gap="sm">
              <TextInput
                label="Полное наименование"
                required
                value={legal.company_name}
                onChange={(e) => setLegal({ ...legal, company_name: e.currentTarget.value })}
              />
              <TextInput
                label="ИНН"
                required
                value={legal.inn}
                onChange={(e) => setLegal({ ...legal, inn: e.currentTarget.value })}
                onBlur={(e) => void lookupInn(e.currentTarget.value)}
                description={lookupBusy ? 'Проверка в реестре…' : 'Автозаполнение через DaData'}
              />
              {mismatches.length > 0 && (
                <Alert color="orange" title="Расхождение с реестром">
                  <Stack gap={4}>
                    {mismatches.map((m) => (
                      <Text key={m.field} size="xs">
                        {m.field}: в реестре «{m.expected}», у вас «{m.actual}»
                      </Text>
                    ))}
                    <Checkbox
                      checked={confirmMismatch}
                      onChange={(e) => setConfirmMismatch(e.currentTarget.checked)}
                      label="Подтверждаю расхождение и продолжаю"
                    />
                  </Stack>
                </Alert>
              )}
              <TextInput
                label="КПП"
                description="Только для ООО"
                value={legal.kpp}
                onChange={(e) => setLegal({ ...legal, kpp: e.currentTarget.value })}
              />
              <TextInput
                label="ОГРН / ОГРНИП"
                required
                value={legal.ogrn}
                onChange={(e) => setLegal({ ...legal, ogrn: e.currentTarget.value })}
              />
              <TextInput
                label="Юридический адрес"
                required
                value={legal.legal_address}
                onChange={(e) => setLegal({ ...legal, legal_address: e.currentTarget.value })}
              />
              <Checkbox
                checked={sameAddress}
                onChange={(e) => setSameAddress(e.currentTarget.checked)}
                label="Фактический адрес совпадает с юридическим"
              />
              {!sameAddress && (
                <TextInput
                  label="Фактический адрес"
                  value={legal.actual_address}
                  onChange={(e) => setLegal({ ...legal, actual_address: e.currentTarget.value })}
                />
              )}
              <TextInput
                label="Банк"
                required
                value={legal.bank_name}
                onChange={(e) => setLegal({ ...legal, bank_name: e.currentTarget.value })}
              />
              <TextInput
                label="БИК"
                required
                value={legal.bik}
                onChange={(e) => setLegal({ ...legal, bik: e.currentTarget.value })}
              />
              <TextInput
                label="Расчётный счёт"
                required
                value={legal.checking_account}
                onChange={(e) => setLegal({ ...legal, checking_account: e.currentTarget.value })}
              />
              <TextInput
                label="Корр. счёт"
                value={legal.corr_account}
                onChange={(e) => setLegal({ ...legal, corr_account: e.currentTarget.value })}
              />
              <TextInput
                label="ФИО руководителя / ИП"
                required
                value={legal.director_name}
                onChange={(e) => setLegal({ ...legal, director_name: e.currentTarget.value })}
              />
              <TextInput
                label="Email для документов"
                type="email"
                value={legal.docs_email}
                onChange={(e) => setLegal({ ...legal, docs_email: e.currentTarget.value })}
              />
            </Stack>
          )}

          <Button loading={loading} onClick={submit}>
            Продолжить
          </Button>
        </Stack>
      </Paper>
    </AuthPage>
  );
}
