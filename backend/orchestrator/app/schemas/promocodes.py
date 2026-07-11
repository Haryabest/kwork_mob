"""Pydantic-схемы промокодов."""

from pydantic import BaseModel


class PromocodeValidateRequest(BaseModel):
    code: str
    order_id: int | None = None
