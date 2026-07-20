# OAuth (VK / Yandex / Sber ID) — ops checklist

## Env (orchestrator)

```env
OAUTH_VK_CLIENT_ID=
OAUTH_VK_CLIENT_SECRET=
OAUTH_YANDEX_CLIENT_ID=
OAUTH_YANDEX_CLIENT_SECRET=
OAUTH_SBER_CLIENT_ID=
OAUTH_SBER_CLIENT_SECRET=
SELLER_PUBLIC_URL=https://seller.example.com
MOBILE_OAUTH_REDIRECT_URI=kworkmob://open/oauth/callback
```

## Redirect URIs (кабинеты провайдеров)

| Платформа | URI |
|-----------|-----|
| Web-seller | `{SELLER_PUBLIC_URL}/auth/oauth/callback` |
| Mobile | `kworkmob://open/oauth/callback` |

## Миграция

```bash
alembic upgrade head   # 036_user_oauth_identities
```

## Smoke

1. `GET /api/v1/auth/oauth/providers` — список провайдеров (пустой без env).
2. Login/register через кнопку на web `/` и mobile `/auth`.
3. Settings → «Привязать» → `GET/POST /auth/oauth/{provider}/link`.
4. Новый OAuth-user: `status=pending_type` → выбор типа аккаунта.

## Примечание

`client_secret` только на backend. Клиенты получают JWT после callback.
