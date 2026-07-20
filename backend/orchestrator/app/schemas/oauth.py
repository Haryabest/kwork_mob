"""OAuth request/response schemas."""

from app.schemas.auth import TokenResponse
from pydantic import BaseModel, Field


class OAuthStartQuery(BaseModel):
    redirect_uri: str | None = None
    platform: str = Field(default="web", pattern=r"^(web|mobile)$")
    mode: str = Field(default="login", pattern=r"^(login|register)$")
    consents: list[str] | None = None


class OAuthStartResponse(BaseModel):
    authorize_url: str
    state: str


class OAuthCallbackBody(BaseModel):
    code: str = Field(min_length=1)
    state: str = Field(min_length=8)
    redirect_uri: str | None = None


class OAuthProvidersResponse(BaseModel):
    items: list[dict[str, str]]


class OAuthTokenResponse(TokenResponse):
    status: str | None = None
    owner_2fa_required: bool = False


class OAuthLinkResponse(BaseModel):
    linked: bool
    provider: str


class OAuthUnlinkResponse(BaseModel):
    unlinked: bool
    provider: str


class OAuthIdentitiesResponse(BaseModel):
    items: list[dict[str, str | None]]
