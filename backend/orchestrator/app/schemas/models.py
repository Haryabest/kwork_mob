"""Pydantic-схемы моделей."""

from pydantic import BaseModel, Field


class ModelRateRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    reasons: list[str] = []
