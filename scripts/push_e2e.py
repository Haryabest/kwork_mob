#!/usr/bin/env python3
"""Push E2E: POST /admin/campaigns/push/test (§3.4.3 / §11.8).

Требования:
  - .env: FCM_SERVER_KEY или FCM_SERVICE_ACCOUNT_JSON + FCM_PROJECT_ID
  - мобильное приложение зарегистрировало токен (POST /user/devices)
  - staff JWT admin

Пример:
  python scripts/push_e2e.py --base http://localhost:8000/api/v1 \\
    --email admin@local --password '...' --user-id 1
"""

from __future__ import annotations

import argparse
import json
import sys

import httpx


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="http://localhost:8000/api/v1")
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--user-id", type=int, default=None)
    p.add_argument("--title", default="KWork Mob E2E")
    p.add_argument("--body", default="Push доставка OK")
    args = p.parse_args()

    with httpx.Client(base_url=args.base.rstrip("/"), timeout=30.0) as client:
        # staff login paths may differ — пробуем /auth/staff/login и /admin/auth/login
        token = None
        for path in ("/auth/staff/login", "/admin/auth/login", "/auth/login"):
            r = client.post(path, json={"email": args.email, "password": args.password})
            if r.status_code < 300:
                data = r.json()
                token = data.get("access_token") or data.get("access") or data.get("token")
                if token:
                    print(f"[push-e2e] login via {path}")
                    break
        if not token:
            print(f"[push-e2e] login failed: {r.status_code} {r.text[:300]}", file=sys.stderr)
            return 1

        headers = {"Authorization": f"Bearer {token}"}
        payload = {"title": args.title, "body": args.body}
        if args.user_id is not None:
            payload["user_id"] = args.user_id
        r = client.post("/admin/campaigns/push/test", json=payload, headers=headers)
        print(json.dumps(r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text}, ensure_ascii=False, indent=2))
        if r.status_code >= 300:
            return 1
        data = r.json()
        if data.get("delivered_push") or data.get("email_fallback"):
            print("[push-e2e] OK")
            return 0
        print("[push-e2e] FAIL: нет push и нет email fallback", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
