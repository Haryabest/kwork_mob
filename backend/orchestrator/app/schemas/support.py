"""Pydantic-схемы поддержки."""

from pydantic import BaseModel, Field


class SupportQuestionRequest(BaseModel):
    message: str = Field(min_length=10)
    subject: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=50)
    attachments: list[str] = []
