# B2B API

## Аутентификация

API-ключ в заголовке: `X-API-Key: {key}`

Scope: `order:create`, `model:read`, `webhook:manage`

## Массовая постановка задач

```
POST /api/v1/company/orders/bulk
```

До 100 задач в JSON.

## Webhooks

События: `model.generated`, `order.created`, `shoot_link.uploaded`, `order.cancelled`

## ERP-интеграция (1С / МойСклад) §14.2

### Сценарии

| Сценарий | API | Webhook |
|----------|-----|---------|
| Создание заказа из ERP | `POST /api/v1/company/orders/bulk` | `order.created` |
| Статус генерации | `GET /api/v1/orders/{id}` | `model.generated` |
| Гостевая съёмка | `POST /api/v1/company/shoot_link` | `shoot_link.uploaded` |

### 1С

- HTTP-соединение к `https://api.{domain}/api/v1/`
- Заголовок `X-API-Key`
- Идемпотентность: `external_id` в теле bulk-заказа

### МойСклад

- Webhook на `model.generated` → обновление карточки товара (URL модели)
- Ошибки 4xx/5xx — retry с exponential backoff на стороне ERP

### Мониторинг

- `GET /api/v1/admin/marketplace/status` — ключи WB/Ozon
- `POST /api/v1/admin/marketplace/e2e-ping` — smoke credentials
