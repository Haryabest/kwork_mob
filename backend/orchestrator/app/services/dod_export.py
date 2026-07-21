"""§1.4 DoD CSV export."""

from __future__ import annotations

import csv
import io
from typing import Any


def dod_to_csv(data: dict[str, Any]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["section", "metric", "value", "pass"])
    w.writerow(["meta", "period_days", data.get("period_days"), ""])
    w.writerow(["meta", "since", data.get("since"), ""])
    summary = data.get("summary") or {}
    for k in ("passed", "total", "ready"):
        w.writerow(["summary", k, summary.get(k), ""])
    for row in data.get("checks") or []:
        w.writerow(["check", row.get("metric"), row.get("value"), row.get("pass")])
    raw = data.get("raw") or {}
    for k, v in raw.items():
        w.writerow(["raw", k, v, ""])
    return buf.getvalue()
