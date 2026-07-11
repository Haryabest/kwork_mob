"""Pydantic-схемы аутентификации."""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).+$")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    password_confirm: str
    # §2.8 — обязательные согласия при регистрации
    consents: list[str] = Field(default_factory=list)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not PASSWORD_PATTERN.match(v):
            raise ValueError("Пароль должен содержать буквы и цифры")
        return v

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.password_confirm:
            raise ValueError("Пароли не совпадают")
        required = {"terms", "privacy", "rights", "nsfw_rules"}
        if not required.issubset(set(self.consents)):
            raise ValueError(
                "Необходимо принять пользовательское соглашение, политику ПДн, "
                "подтверждение прав и правила запрещённого контента"
            )
        return self


class RegisterResponse(BaseModel):
    message: str
    email: EmailStr
    dev_code: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False
    remember: bool | None = None

    @model_validator(mode="after")
    def sync_remember(self):
        if self.remember is not None:
            self.remember_me = self.remember
        return self


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class VerifyEmailResponse(BaseModel):
    message: str
    status: str
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"


class AccountTypeRequest(BaseModel):
    account_type: str = Field(pattern=r"^(individual|legal)$")
    full_name: str | None = None
    inn: str | None = None
    # Юрлицо / ИП (§2.2.2)
    company_name: str | None = None
    kpp: str | None = None
    ogrn: str | None = None
    legal_address: str | None = None
    actual_address: str | None = None
    bank_name: str | None = None
    bik: str | None = None
    checking_account: str | None = None
    corr_account: str | None = None
    director_name: str | None = None
    docs_email: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordConfirmRequest(BaseModel):
    token: str
    new_password: str | None = Field(default=None, min_length=8)
    password: str | None = Field(default=None, min_length=8)
    password_confirm: str | None = None

    @model_validator(mode="after")
    def resolve_password(self):
        pwd = self.new_password or self.password
        if not pwd:
            raise ValueError("Укажите новый пароль")
        if self.password_confirm is not None and pwd != self.password_confirm:
            raise ValueError("Пароли не совпадают")
        if not PASSWORD_PATTERN.match(pwd):
            raise ValueError("Пароль должен содержать буквы и цифры")
        self.new_password = pwd
        return self


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
