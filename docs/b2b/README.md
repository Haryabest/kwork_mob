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

## ERP-интеграция

1С, МойСклад — через REST API + webhook.
