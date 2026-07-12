"""Pydantic-схемы промокодов."""

from pydantic import BaseModel, Field


class PromocodeValidateRequest(BaseModel):
    code: str = Field(min_length=4, max_length=64)
    order_id: int | None = None
    tier: str | None = Field(default=None, pattern="^(small|large)$")
