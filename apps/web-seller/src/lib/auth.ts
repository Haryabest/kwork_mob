'use client';

const ACCESS_TOKEN = 'access_token';
const REFRESH_TOKEN = 'refresh_token';

function storage() {
  return typeof window === 'undefined' ? null : window.localStorage;
}

export const auth = {
  getAccessToken: () => storage()?.getItem(ACCESS_TOKEN) ?? null,
  getRefreshToken: () => storage()?.getItem(REFRESH_TOKEN) ?? null,
  setTokens(accessToken: string, refreshToken: string) {
    storage()?.setItem(ACCESS_TOKEN, accessToken);
    storage()?.setItem(REFRESH_TOKEN, refreshToken);
  },
  clear() {
    storage()?.removeItem(ACCESS_TOKEN);
    storage()?.removeItem(REFRESH_TOKEN);
  },
};
