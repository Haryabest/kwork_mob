# API-документация

OpenAPI-спецификация:

- Интерактивно (Swagger UI): `http://localhost:8000/api/docs`
- Версионированный контракт в git: [`openapi.json`](./openapi.json) и [`openapi.yaml`](./openapi.yaml) (270+ путей)

Перегенерация спеки после изменения API:

```bash
cd backend/orchestrator
python scripts/export_openapi.py           # запись docs/api/openapi.json (+.yaml)
python scripts/export_openapi.py --check    # CI-проверка актуальности
```

Из `openapi.json` генерируются клиенты (openapi-generator / orval) без запуска сервера.

## Группы эндпоинтов

| Группа | Prefix | Описание |
|--------|--------|----------|
| Аутентификация | `/api/v1/auth` | Регистрация, вход, JWT |
| Пользователь | `/api/v1/user` | Баланс, модели |
| Компания | `/api/v1/company` | Команда, API-ключи, съёмка по ссылке |
| Заказы | `/api/v1/orders` | Создание, статус, отмена |
| Модели | `/api/v1/models` | Скачивание, публикация, оценка |
| Промокоды | `/api/v1/promocodes` | Валидация |
| Поддержка | `/api/v1/support` | Вопросы |
| FAQ | `/api/v1/faq` | Публичный FAQ |
| Админ | `/api/v1/admin` | B2B, воркеры, модерация |
| Webhooks | `/api/v1/webhooks` | ЮKassa |
| WebSocket | `/ws/queue/{user_id}`, `/ws/worker` | Real-time |

Полный список — см. `ТЗ.txt`, раздел 4.1.1.
