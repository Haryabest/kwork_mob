'use client';

/** JWT в httpOnly cookies (§20.10.2) — клиент не хранит токены. */

export const auth = {
  getAccessToken: () => null as string | null,
  getRefreshToken: () => null as string | null,
  setTokens(_accessToken: string, _refreshToken: string) {
    /* cookies выставляет backend */
  },
  clear() {
    /* logout endpoint очищает cookies */
  },
  async logout(apiPost: (url: string, body?: object) => Promise<unknown>) {
    try {
      await apiPost('/auth/logout', {});
    } catch {
      /* ignore */
    }
    this.clear();
  },
};
