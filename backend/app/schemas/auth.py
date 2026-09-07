from uuid import UUID
from pydantic import AliasChoices, BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None


class UserUpdateRequest(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    phone: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    message: str
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    user_id: UUID
    name: str
    email: EmailStr
    phone: str | None = None
    role_id: UUID
    is_active: bool
    is_email_verified: bool

    class Config:
        from_attributes = True


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
