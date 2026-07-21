#!/usr/bin/env python3
"""HA witness / quorum arbiter §22.5 — пингует узлы хранения."""

from __future__ import annotations

import json
import os
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer


def _nodes() -> list[str]:
    raw = os.getenv("WITNESS_NODES", "minio-1:9000,minio-2:9000,postgres-primary:5432")
    return [x.strip() for x in raw.split(",") if x.strip()]


def _ping(host_port: str) -> bool:
    if ":" not in host_port:
        return False
    host, port_s = host_port.rsplit(":", 1)
    try:
        port = int(port_s)
    except ValueError:
        return False
    try:
        with socket.create_connection((host, port), timeout=float(os.getenv("WITNESS_TIMEOUT", "2"))):
            return True
    except OSError:
        return False


class WitnessHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # noqa: ARG002
        return

    def do_GET(self) -> None:
        if self.path not in ("/", "/health", "/quorum"):
            self.send_response(404)
            self.end_headers()
            return
        nodes = _nodes()
        status = {n: _ping(n) for n in nodes}
        online = sum(1 for v in status.values() if v)
        # split-brain guard: failover only if witness sees ≤1 node down (not network partition of witness)
        quorum_ok = online >= max(1, len(nodes) - 1)
        body = {
            "nodes": status,
            "online_count": online,
            "total": len(nodes),
            "quorum_ok": quorum_ok,
            "both_storage_online": online == len(nodes) and len(nodes) >= 2,
        }
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    port = int(os.getenv("WITNESS_PORT", "8089"))
    HTTPServer(("0.0.0.0", port), WitnessHandler).serve_forever()


if __name__ == "__main__":
    main()
