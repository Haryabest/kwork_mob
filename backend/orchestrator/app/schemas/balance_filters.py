"""Saved balance transaction filter payloads §20.3.4."""

from pydantic import BaseModel, Field


class BalanceFiltersBody(BaseModel):
    date_from: str = Field(default="", max_length=10)
    date_to: str = Field(default="", max_length=10)
    tx_type: str = Field(default="all", pattern=r"^(all|topup|charge|refund)$")
    page_size: int = Field(default=20, ge=20, le=100)


class CompanyBalanceFiltersBody(BalanceFiltersBody):
    author_id: int | None = Field(default=None, ge=1)
