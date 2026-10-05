import os
import hashlib
import hmac
import secrets
from uuid import UUID
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pwdlib import PasswordHash
import jwt
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DEFAULT_JWT_SECRET = "roadsense-ai-jwt-secret-key-change-in-production"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def get_jwt_settings() -> tuple[str, str]:
    secret_key = os.getenv("JWT_SECRET_KEY") or DEFAULT_JWT_SECRET

    return secret_key, os.getenv("JWT_ALGORITHM", "HS256")


def create_access_token(user_id: UUID | str | int) -> str:
    secret_key, algorithm = get_jwt_settings()
    configured_expire_minutes = int(
        os.getenv(
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            str(ACCESS_TOKEN_EXPIRE_MINUTES)
        )
    )
    if configured_expire_minutes <= 0:
        raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive.")
    expire_minutes = min(
        configured_expire_minutes,
        ACCESS_TOKEN_EXPIRE_MINUTES
    )

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expire_minutes
    )

    payload = {
        "user_id": str(user_id),
        "exp": expire
    }

    return jwt.encode(
        payload,
        secret_key,
        algorithm=algorithm
    )


security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UUID:
    token = credentials.credentials

    try:
        secret_key, algorithm = get_jwt_settings()

        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm]
        )

        user_id_raw = payload.get("user_id")

        if user_id_raw is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token payload. Please log in again."
            )

        try:
            return UUID(str(user_id_raw))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed user ID in authentication token. Please log in again."
            )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your authentication session has expired. Please log in again."
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token. Please log in to continue."
        )


def create_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str) -> str:
    """Hash an OTP with the application secret before storing it."""
    secret_key, _ = get_jwt_settings()
    return hmac.new(secret_key.encode(), otp.encode(), hashlib.sha256).hexdigest()


def verify_otp(otp: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(otp), expected_hash)


def get_current_user_obj(
    user_id: UUID = Depends(get_current_user)
):
    from sqlalchemy.orm import joinedload
    from app.database.connection import SessionLocal
    from app.database.models import User

    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .options(joinedload(User.role))
            .filter(User.user_id == user_id)
            .first()
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found. Please register or log in again."
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your user account has been deactivated. Please contact an administrator."
            )
        # Ensure role relationship is populated before detaching
        if user.role:
            _ = user.role.role_name
            db.expunge(user.role)
        db.expunge(user)
        return user
    finally:
        db.close()


def require_roles(*allowed_roles: str):
    """
    Dependency factory to enforce Role-Based Access Control (RBAC).
    Allowed roles e.g.: 'SUPER_ADMIN', 'TRAFFIC_AUTHORITY', 'EMERGENCY_RESPONSE', 'VIEWER'.
    """
    normalized_allowed = {r.strip().upper() for r in allowed_roles}

    def role_checker(
        current_user = Depends(get_current_user_obj)
    ):
        role_name = current_user.role.role_name.strip().upper() if current_user.role else ""
        if role_name not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: This action requires one of the following permissions: {', '.join(allowed_roles)}. Your current role ({role_name or 'None'}) is not authorized."
            )
        return current_user

    return role_checker
