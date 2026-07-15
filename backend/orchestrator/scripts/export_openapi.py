"""Экспорт OpenAPI-спеки FastAPI в docs/api (§15).

Использование:
    python scripts/export_openapi.py            # запись openapi.json (+.yaml, если есть pyyaml)
    python scripts/export_openapi.py --check     # CI: упасть, если спека в git устарела

Спека версионируется в git (docs/api/openapi.json), чтобы диффы контракта
были видны в ревью и чтобы генерировать клиентов без запуска сервера.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
OUT_DIR = REPO_ROOT / "docs" / "api"
JSON_PATH = OUT_DIR / "openapi.json"
YAML_PATH = OUT_DIR / "openapi.yaml"


def build_spec() -> dict:
    # Импорт внутри функции, чтобы --help работал без зависимостей приложения.
    sys.path.insert(0, str(ROOT))
    from app.main import app

    return app.openapi()


def _dump_json(spec: dict) -> str:
    return json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export OpenAPI spec")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Проверить, что записанная спека совпадает с текущей (для CI)",
    )
    args = parser.parse_args()

    spec = build_spec()
    payload = _dump_json(spec)

    if args.check:
        if not JSON_PATH.exists():
            print(f"[openapi] {JSON_PATH} отсутствует — запустите export без --check", file=sys.stderr)
            return 1
        current = JSON_PATH.read_text(encoding="utf-8")
        if current != payload:
            print("[openapi] спека устарела: перегенерируйте docs/api/openapi.json", file=sys.stderr)
            return 1
        print("[openapi] спека актуальна")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(payload, encoding="utf-8")
    paths = len(spec.get("paths", {}))
    print(f"[openapi] {JSON_PATH} записан ({paths} путей)")

    try:
        import yaml  # type: ignore

        YAML_PATH.write_text(
            yaml.safe_dump(spec, allow_unicode=True, sort_keys=True), encoding="utf-8"
        )
        print(f"[openapi] {YAML_PATH} записан")
    except Exception:
        print("[openapi] pyyaml не установлен — .yaml пропущен")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
