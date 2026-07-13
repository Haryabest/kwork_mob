"""
Locust B2B load harness (§21 DoD).

  locust -f scripts/load/locustfile.py --host=http://localhost:8000

Env:
  LOAD_TOKEN, LOAD_COMPANY_ID
"""

from __future__ import annotations

import os
import uuid

from locust import HttpUser, between, task

TOKEN = os.getenv("LOAD_TOKEN", "")
COMPANY_ID = int(os.getenv("LOAD_COMPANY_ID", "1"))


class B2BUser(HttpUser):
    wait_time = between(0.3, 1.2)

    def on_start(self):
        self.headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        }

    @task(3)
    def shoot_link(self):
        with self.client.post(
            "/api/v1/company/shoot_link",
            json={
                "company_id": COMPANY_ID,
                "category": "other",
                "tier": "small",
                "ttl_hours": 24,
                "max_uses": 1,
            },
            headers=self.headers,
            name="POST /company/shoot_link",
            catch_response=True,
        ) as resp:
            if resp.status_code >= 500:
                resp.failure(f"5xx {resp.status_code}")
            elif resp.elapsed.total_seconds() > 1.0:
                resp.failure(f"slow {resp.elapsed.total_seconds():.2f}s > 1s")
            else:
                resp.success()

    @task(2)
    def prepare_and_create_order(self):
        task_uuid = str(uuid.uuid4())
        self.client.post(
            "/api/v1/orders/photos/prepare",
            json={"task_uuid": task_uuid},
            headers=self.headers,
            name="POST /orders/photos/prepare",
        )
        with self.client.post(
            "/api/v1/orders/create",
            json={
                "task_uuid": task_uuid,
                "category": "other",
                "tier": "small",
                "company_id": COMPANY_ID,
                "forbidden_categories": [],
                "upsell_options": [],
            },
            headers=self.headers,
            name="POST /orders/create",
            catch_response=True,
        ) as resp:
            if resp.status_code >= 500:
                resp.failure(f"5xx {resp.status_code}")
            else:
                resp.success()

    @task(1)
    def company_mine(self):
        self.client.get(
            "/api/v1/company/mine",
            headers=self.headers,
            name="GET /company/mine",
        )
