import re
from datetime import datetime
from uuid import UUID
from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, field_validator

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


def validate_password_strength(password: str, min_len: int = 8, field_name: str = "Password") -> str:
    if not isinstance(password, str):
        raise ValueError(f"{field_name} must be a valid text string.")
    if len(password) < min_len:
        raise ValueError(f"{field_name} must be at least {min_len} characters long.")
    if len(password) > 128:
        raise ValueError(f"{field_name} cannot exceed 128 characters.")
    for ch in password:
        code = ord(ch)
        if code < 32 or code == 127:
            raise ValueError(
                f"{field_name} cannot contain control characters, raw line breaks, or unescaped tabs."
            )
    if not password.strip():
        raise ValueError(f"{field_name} cannot be blank or composed only of whitespace.")
    return password


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None

    @field_validator("phone", mode="before")
    @classmethod
    def validate_optional_phone(cls, value: str | None) -> str | None:
        return validate_phone_number(value)

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, value: str) -> str:
        return validate_password_strength(value, min_len=6, field_name="Password")


class UserProfileUpdate(BaseModel):
    """Fields account owners and Super Admins may edit through profile routes."""

    model_config = ConfigDict(extra="forbid")

    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_.-]+$",
    )
    name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = None

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Username cannot be null.")
        if not isinstance(value, str):
            raise ValueError("Username must be text.")
        value = value.strip().lower()
        if not value:
            raise ValueError("Username cannot be blank.")
        return value

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Name cannot be null.")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Name cannot be blank.")
        return value.strip()

    @field_validator("phone", mode="before")
    @classmethod
    def validate_optional_phone(cls, value: str | None) -> str | None:
        return validate_phone_number(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    user_id: UUID
    username: str | None = None
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

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_strength(value, min_len=8, field_name="New password")
