import re
from datetime import datetime
from uuid import UUID
from pydantic import AliasChoices, BaseModel, EmailStr, Field, field_validator

PHONE_REGEX = re.compile(r"^(\+91[\-\s]?|0)?[6-9]\d{9}$|^[0-9]{10}$")


def validate_phone_number(value: str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        val = value.strip()
        if not val:
            return None
        cleaned = re.sub(r"[\s\-()]", "", val)
        if not PHONE_REGEX.match(cleaned):
            raise ValueError("Phone number must be a valid 10-digit number.")
        return cleaned
    raise ValueError("Phone number must be a valid string.")


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None

    @field_validator("phone", mode="before")
    @classmethod
    def validate_optional_phone(cls, value: str | None) -> str | None:
        return validate_phone_number(value)


class UserUpdateRequest(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    phone: str | None = None

    @field_validator("phone", mode="before")
    @classmethod
    def validate_optional_phone(cls, value: str | None) -> str | None:
        return validate_phone_number(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    user_id: UUID
    name: str
    email: EmailStr
    phone: str | None = None
    role_id: UUID
    role_name: str | None = None
    is_active: bool
    is_email_verified: bool

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    message: str
    access_token: str
    token_type: str = "bearer"
    login_at: datetime
    user: UserResponse


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")

    @field_validator("otp", mode="before")
    @classmethod
    def normalize_otp(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_password: str = Field(validation_alias=AliasChoices("new_password", "newPassword"))

    @field_validator("otp", mode="before")
    @classmethod
    def normalize_otp(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value
