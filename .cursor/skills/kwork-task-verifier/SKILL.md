---
name: kwork-task-verifier
description: Проверяет, выполнены ли задачи P{N} в kwork_mob (grep, тесты, API). Use before claiming a batch done, or when user asks to verify tasks are not duplicate or are complete.
---

# Kwork Task Verifier

## Когда использовать

- Перед началом среза: «не сделаны ли уже»
- После реализации: «всё ли готово»
- Пользователь просит проверить P{N}

## Checklist на задачу

Для каждой задачи из `СЛЕДУЮЩИЕ_ЗАДАЧИ.md`:

1. **Grep** — endpoint/UI/поле из описания есть в коде?
2. **Не дубль** — нет в последних итерациях `чтоготовосегодня.md`?
3. **Тест** — slice test проходит (backend)?
4. **OpenAPI** — путь в `docs/api/openapi.yaml` (если API)?

## Команды

```bash
cd backend/orchestrator
python -m pytest tests/test_*_slice.py -q
python scripts/export_openapi.py
```

```bash
rg "pattern" apps/ backend/ --glob "*.{py,tsx,dart}"
```

## Вердикт

| Статус | Действие |
|--------|----------|
| NOT DONE | Можно кодить |
| PARTIAL | Дописать недостающее |
| DONE | Пропустить; взять P{N+1} |

## Отчёт пользователю

Краткая таблица: задача | статус | доказательство (файл/тест).
