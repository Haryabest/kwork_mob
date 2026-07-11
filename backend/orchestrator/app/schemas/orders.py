"""Pydantic-схемы заказов."""

from enum import Enum

from pydantic import BaseModel, Field


class ProductCategory(str, Enum):
    CLOTHING = "clothing"
    SHOES = "shoes"
    ELECTRONICS = "electronics"
    FURNITURE = "furniture"
    DECOR = "decor"
    TOYS = "toys"
    ADULT = "adult"
    OTHER = "other"


class ForbiddenCategory(str, Enum):
    INTIMATE = "intimate"
    WEAPONS = "weapons"
    DRUGS = "drugs"


class Tier(str, Enum):
    SMALL = "small"
    LARGE = "large"


class UpsellOption(str, Enum):
    REAL_SCALE = "real_scale"
    VIDEO_360 = "video_360"
    VIRTUAL_TRYON = "virtual_tryon"
    HOLE_FILLING = "hole_filling"


class OrderCreateRequest(BaseModel):
    category: ProductCategory
    tier: Tier
    company_id: int | None = None
    promocode: str | None = None
    upsell_options: list[UpsellOption] = []
    forbidden_categories: list[ForbiddenCategory] = []
    birth_date: str | None = None  # для 18+
    scale_calibration: dict | None = None
    task_uuid: str = Field(description="UUID для идемпотентности")
