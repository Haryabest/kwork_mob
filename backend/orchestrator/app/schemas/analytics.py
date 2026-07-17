"""Mobile analytics event batch §19.20."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

ALLOWED_EVENTS = frozenset(
    {"screen_view", "shoot_complete", "checkout_pay", "shoot_step", "shoot_step_retry"}
)

# screen_view.props.screen — каталог §19.20 (mobile track + admin breakdown)
ALLOWED_SCREENS = frozenset(
    {
        "home",
        "models",
        "orders",
        "support",
        "profile",
        "settings",
        "queue",
        "queue_refresh",
        "balance",
        "storage",
        "notifications",
        "api_keys",
        "team",
        "company_topup",
        "company_policies",
        "import",
        "trash",
        "model_viewer",
        "publish_guide",
        "shoot_link",
        "shoot_link_fab",
        "shoot_category",
        "shoot_upload",
        "shoot_dome",
        "shoot_quality",
        "order_checkout",
        "guest_shoot",
        "calibration",
        "consent_gate",
        "faq_support",
        "campaign_banner",
        "campaign_banner_click",
        "campaign_banner_dismiss",
        "pending_upload_banner",
        "pending_upload_continue",
        "export_prefs",
        "export_prefs_save",
        "mode_personal",
        "mode_corporate",
    }
)


class AnalyticsEventItem(BaseModel):
    event: str = Field(min_length=1, max_length=64)
    ts: str = Field(min_length=10, max_length=40)
    props: dict[str, object] | None = None

    @field_validator("ts")
    @classmethod
    def parse_ts(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("invalid ts") from exc
        return v

    @model_validator(mode="after")
    def validate_props(self) -> AnalyticsEventItem:
        if self.event not in ALLOWED_EVENTS:
            raise ValueError(f"unknown event: {self.event}")
        props = self.props or {}
        if self.event == "screen_view":
            screen = props.get("screen")
            if not isinstance(screen, str) or not screen.strip():
                raise ValueError("screen_view requires props.screen")
            if len(screen) > 64:
                raise ValueError("props.screen too long")
            if screen not in ALLOWED_SCREENS:
                raise ValueError(f"unknown screen: {screen}")
            bid = props.get("banner_id")
            if bid is not None and not isinstance(bid, int):
                raise ValueError("props.banner_id must be int")
        elif self.event == "shoot_complete":
            uuid = props.get("model_uuid")
            if not isinstance(uuid, str) or not uuid.strip():
                raise ValueError("shoot_complete requires props.model_uuid")
        elif self.event == "checkout_pay":
            if props.get("order_id") is None:
                raise ValueError("checkout_pay requires props.order_id")
        elif self.event == "shoot_step":
            uuid = props.get("model_uuid")
            step = props.get("step")
            if not isinstance(uuid, str) or not uuid.strip():
                raise ValueError("shoot_step requires props.model_uuid")
            if not isinstance(step, int) or step < 1 or step > 12:
                raise ValueError("shoot_step requires props.step 1..12")
        elif self.event == "shoot_step_retry":
            uuid = props.get("model_uuid")
            step = props.get("step")
            err = props.get("error_type")
            if not isinstance(uuid, str) or not uuid.strip():
                raise ValueError("shoot_step_retry requires props.model_uuid")
            if not isinstance(step, int) or step < 1 or step > 12:
                raise ValueError("shoot_step_retry requires props.step 1..12")
            if not isinstance(err, str) or not err.strip():
                raise ValueError("shoot_step_retry requires props.error_type")
        return self


class AnalyticsEventsBody(BaseModel):
    events: list[AnalyticsEventItem] = Field(default_factory=list, max_length=200)
