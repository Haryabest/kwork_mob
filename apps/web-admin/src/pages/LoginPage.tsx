import {
  Alert,
  Button,
  Code,
  Image,
  Paper,
  PasswordInput,
  PinInput,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { IconInfoCircle, IconLock, IconShieldLock } from '@tabler/icons-react';
import { FormEvent, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { defaultRouteFor } from '../auth/roles';

type Step = 'credentials' | 'setup' | 'verify';

export default function LoginPage() {
  const { user, vpnStatus, startLogin, setup2fa, confirm2fa, verify2fa } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [step, setStep] = useState<Step>('credentials');
  const [challenge, setChallenge] = useState('');
  const [qr, setQr] = useState('');
  const [secret, setSecret] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [hint, setHint] = useState('');

  if (user) {
    return <Navigate to={defaultRouteFor(user.role)} replace />;
  }

  async function onCredentials(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const result = await startLogin(email, password);
      if (result.status === 'ok') {
        navigate('/');
        return;
      }
      setHint(result.message ?? '');
      setCode('');
      if (result.status === 'setup_2fa') {
        const setup = await setup2fa(result.challenge_token);
        setChallenge(setup.challenge_token);
        setQr(setup.qr_data_url);
        setSecret(setup.secret);
        setHint(setup.message ?? result.message ?? '');
        setStep('setup');
      } else {
        setChallenge(result.challenge_token);
        setQr('');
        setSecret('');
        setStep('verify');
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Не удалось выполнить вход');
    } finally {
      setLoading(false);
    }
  }

  async function onTotp(e: FormEvent) {
    e.preventDefault();
    if (code.length < 6) {
      setError('Введите 6-значный код');
      return;
    }
    setLoading(true);
    setError('');
    try {
      if (step === 'setup') {
        await confirm2fa(challenge, code);
      } else {
        await verify2fa(challenge, code);
      }
      navigate('/');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Неверный код');
    } finally {
      setLoading(false);
    }
  }

  const vpnBlocked = Boolean(vpnStatus?.vpn_required && !vpnStatus.vpn_ok);

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'grid',
        placeItems: 'center',
        background:
          'radial-gradient(circle at 20% 20%, rgba(11,122,115,0.14), transparent 42%), radial-gradient(circle at 80% 80%, rgba(15,76,92,0.10), transparent 40%), #f4f7f7',
        padding: 16,
      }}
    >
      <Paper shadow="md" radius="lg" p="xl" w={440} maw="100%" withBorder>
        <Stack gap="md">
          <div>
            <Title order={2}>Staff Panel</Title>
            <Text c="dimmed" size="sm">
              VPN (WireGuard/Tailscale) + 2FA (TOTP) · JWT 8ч · idle 30 мин
            </Text>
          </div>

          {vpnBlocked ? (
            <Alert icon={<IconShieldLock size={16} />} color="red" variant="light">
              Доступ только через VPN. Ваш IP ({vpnStatus?.ip}) не в разрешённой сети.
            </Alert>
          ) : (
            <Alert icon={<IconInfoCircle size={16} />} color="brand" variant="light">
              {vpnStatus?.vpn_required
                ? `VPN OK (${vpnStatus.ip}). Далее пароль и код Authenticator.`
                : 'VPN в этом окружении не обязателен (ADMIN_VPN_REQUIRED=false). 2FA обязательна.'}
            </Alert>
          )}

          {error && <Alert color="red">{error}</Alert>}
          {hint && step !== 'credentials' && (
            <Alert icon={<IconLock size={16} />} color="blue" variant="light">
              {hint}
            </Alert>
          )}

          {step === 'credentials' && (
            <form onSubmit={onCredentials}>
              <Stack gap="sm">
                <TextInput
                  label="Email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.currentTarget.value)}
                  required
                  placeholder="admin@example.com"
                  disabled={vpnBlocked}
                />
                <PasswordInput
                  label="Пароль"
                  value={password}
                  onChange={(e) => setPassword(e.currentTarget.value)}
                  required
                  placeholder="••••••••"
                  disabled={vpnBlocked}
                />
                <Button type="submit" fullWidth loading={loading} mt="xs" disabled={vpnBlocked}>
                  Войти
                </Button>
              </Stack>
            </form>
          )}

          {step === 'setup' && (
            <Stack gap="sm">
              <Text size="sm">Отсканируйте QR в Google Authenticator / Authy:</Text>
              {qr && <Image src={qr} alt="TOTP QR" w={200} mx="auto" />}
              {secret && (
                <Text size="xs" c="dimmed" ta="center">
                  Или введите секрет вручную: <Code>{secret}</Code>
                </Text>
              )}
              <form onSubmit={onTotp}>
                <Stack gap="sm" align="center">
                  <Text size="sm">Подтвердите кодом из приложения</Text>
                  <PinInput length={6} type="number" value={code} onChange={setCode} oneTimeCode />
                  <Button type="submit" fullWidth loading={loading} disabled={code.length < 6}>
                    Подтвердить и войти
                  </Button>
                  <Button
                    variant="subtle"
                    onClick={() => {
                      setStep('credentials');
                      setChallenge('');
                      setQr('');
                      setCode('');
                    }}
                  >
                    Назад
                  </Button>
                </Stack>
              </form>
            </Stack>
          )}

          {step === 'verify' && (
            <form onSubmit={onTotp}>
              <Stack gap="sm" align="center">
                <Text size="sm">Код из приложения-аутентификатора</Text>
                <PinInput length={6} type="number" value={code} onChange={setCode} oneTimeCode />
                <Button type="submit" fullWidth loading={loading} disabled={code.length < 6}>
                  Подтвердить
                </Button>
                <Button
                  variant="subtle"
                  onClick={() => {
                    setStep('credentials');
                    setChallenge('');
                    setCode('');
                  }}
                >
                  Назад
                </Button>
              </Stack>
            </form>
          )}
        </Stack>
      </Paper>
    </div>
  );
}
