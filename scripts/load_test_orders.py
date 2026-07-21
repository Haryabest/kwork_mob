#!/usr/bin/env python3
"""§1.4 Load test: POST /admin/load-test/queue (100 synthetic orders)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description="Enqueue N synthetic orders via admin API")
    parser.add_argument("--base-url", default=os.getenv("API_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--token", default=os.getenv("ADMIN_TOKEN", ""))
    parser.add_argument("--count", type=int, default=100)
    args = parser.parse_args()
    if not args.token:
        print("Set ADMIN_TOKEN or --token", file=sys.stderr)
        return 1
    url = f"{args.base_url.rstrip('/')}/api/v1/admin/load-test/queue?count={args.count}"
    req = urllib.request.Request(url, method="POST", headers={"Authorization": f"Bearer {args.token}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        print(exc.read().decode(), file=sys.stderr)
        return exc.code
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0 if data.get("enqueued", 0) >= args.count else 2


if __name__ == "__main__":
    raise SystemExit(main())
