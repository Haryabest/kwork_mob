import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { StaffRole } from './roles';
import { api, authStorage, getApiError } from '../services/api';

const IDLE_MS = 30 * 60 * 1000;
const ACTIVITY_KEY = 'staff_last_activity';

export interface StaffUser {
  email: string;
  role: StaffRole;
  id?: string | number;
}

export type StaffLoginResult =
  | { status: 'ok' }
  | { status: 'need_2fa'; challenge_token: string; message?: string }
  | { status: 'setup_2fa'; challenge_token: string; message?: string };

export interface TotpSetupResult {
  challenge_token: string;
  secret: string;
  qr_data_url: string;
  otpauth_uri?: string;
  message?: string;
}

interface AuthContextValue {
  user: StaffUser | null;
  vpnStatus: { vpn_required: boolean; vpn_ok: boolean; ip?: string } | null;
  startLogin: (email: string, password: string) => Promise<StaffLoginResult>;
  setup2fa: (challengeToken: string) => Promise<TotpSetupResult>;
  confirm2fa: (challengeToken: string, code: string) => Promise<void>;
  verify2fa: (challengeToken: string, code: string) => Promise<void>;
  logout: () => void;
  touchActivity: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function toStaffUser(data: Record<string, unknown>): StaffUser {
  const role = data.staff_role ?? data.role;
  if (role !== 'admin' && role !== 'support_agent') {
    throw new Error('Доступ разрешён только сотрудникам панели');
  }
  return {
    id: data.id as string | number | undefined,
    email: String(data.email ?? ''),
    role,
  };
}

async function loadMeAndSet(
  setUser: (u: StaffUser | null) => void,
  access: string,
  refresh?: string,
) {
  authStorage.save(access, refresh);
  try {
    const { data } = await api.get('/user/me');
    const staff = toStaffUser(data);
    localStorage.setItem('staff_user', JSON.stringify(staff));
    localStorage.setItem(ACTIVITY_KEY, String(Date.now()));
    setUser(staff);
  } catch (error) {
    authStorage.clear();
    throw error;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<StaffUser | null>(() => {
    const raw = localStorage.getItem('staff_user');
    if (!raw) return null;
    try {
      return toStaffUser(JSON.parse(raw) as Record<string, unknown>);
    } catch {
      authStorage.clear();
      return null;
    }
  });
  const [vpnStatus, setVpnStatus] = useState<AuthContextValue['vpnStatus']>(null);

  useEffect(() => {
    api
      .get('/staff/vpn-status')
      .then(({ data }) =>
        setVpnStatus({
          vpn_required: Boolean(data.vpn_required),
          vpn_ok: Boolean(data.vpn_ok),
          ip: data.ip,
        }),
      )
      .catch(() => setVpnStatus(null));
  }, []);

  useEffect(() => {
    if (!user) return;

    const checkIdle = () => {
      const last = Number(localStorage.getItem(ACTIVITY_KEY) || 0);
      if (last && Date.now() - last > IDLE_MS) {
        authStorage.clear();
        setUser(null);
      }
    };

    const onActivity = () => {
      localStorage.setItem(ACTIVITY_KEY, String(Date.now()));
    };

    checkIdle();
    const id = window.setInterval(checkIdle, 60_000);
    window.addEventListener('mousemove', onActivity);
    window.addEventListener('keydown', onActivity);
    window.addEventListener('click', onActivity);
    return () => {
      window.clearInterval(id);
      window.removeEventListener('mousemove', onActivity);
      window.removeEventListener('keydown', onActivity);
      window.removeEventListener('click', onActivity);
    };
  }, [user]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      vpnStatus,
      touchActivity() {
        localStorage.setItem(ACTIVITY_KEY, String(Date.now()));
      },
      async startLogin(email: string, password: string) {
        try {
          const { data } = await api.post('/staff/login', { email, password });
          if (data.status === 'ok') {
            await loadMeAndSet(setUser, data.access_token, data.refresh_token);
            return { status: 'ok' };
          }
          if (data.status === 'setup_2fa' || data.status === 'need_2fa') {
            return {
              status: data.status,
              challenge_token: data.challenge_token,
              message: data.message,
            };
          }
          throw new Error('Неожиданный ответ сервера');
        } catch (error) {
          throw new Error(getApiError(error));
        }
      },
      async setup2fa(challengeToken: string) {
        try {
          const { data } = await api.post('/staff/2fa/setup', { challenge_token: challengeToken });
          return data as TotpSetupResult;
        } catch (error) {
          throw new Error(getApiError(error));
        }
      },
      async confirm2fa(challengeToken: string, code: string) {
        try {
          const { data } = await api.post('/staff/2fa/confirm', {
            challenge_token: challengeToken,
            code,
          });
          await loadMeAndSet(setUser, data.access_token, data.refresh_token);
        } catch (error) {
          throw new Error(getApiError(error));
        }
      },
      async verify2fa(challengeToken: string, code: string) {
        try {
          const { data } = await api.post('/staff/2fa/verify', {
            challenge_token: challengeToken,
            code,
          });
          await loadMeAndSet(setUser, data.access_token, data.refresh_token);
        } catch (error) {
          throw new Error(getApiError(error));
        }
      },
      logout() {
        authStorage.clear();
        setUser(null);
      },
    }),
    [user, vpnStatus],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth вне AuthProvider');
  return ctx;
}
