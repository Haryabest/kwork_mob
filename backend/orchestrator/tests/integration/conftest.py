"""Shared helpers for integration smoke tests."""

from __future__ import annotations

import uuid

LEGAL_COMPANY_TEMPLATE = {
    "account_type": "legal",
    "company_name": "Dev Org {inn}",
    "inn": "{inn}",
    "kpp": "770101001",
    "ogrn": "1027700132195",
    "legal_address": "г. Москва, ул. Примерная, д. 1",
    "director_name": "Иванов Иван Иванович",
    "bank_name": "Тест Банк",
    "bik": "044525225",
    "checking_account": "40702810123456789012",
}


async def login_owner_with_company(client, unique_email):
    email = unique_email()
    password = "secret123"
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "password_confirm": password,
            "consents": ["terms", "privacy", "offer", "rights", "nsfw_rules"],
        },
    )
    assert reg.status_code == 201
    await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": reg.json()["dev_code"]},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    inn = f"{uuid.uuid4().int % 10**10:010d}"
    body = {k: v.format(inn=inn) if isinstance(v, str) and "{inn}" in v else v for k, v in LEGAL_COMPANY_TEMPLATE.items()}
    at = await client.post("/api/v1/auth/account-type", headers=headers, json=body)
    assert at.status_code == 200, at.text
    return headers
