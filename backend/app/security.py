import os
from uuid import UUID
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pwdlib import PasswordHash
import jwt
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DEFAULT_JWT_SECRET = "roadsense-ai-jwt-secret-key-change-in-production"
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
    expire_minutes = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
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
                detail="Invalid token"
            )

        try:
            return UUID(str(user_id_raw))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


def create_password_reset_token(user_id: UUID | str | int) -> str:
    secret_key, algorithm = get_jwt_settings()

    expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    payload = {
        "user_id": str(user_id),
        "purpose": "password_reset",
        "exp": expire
    }

    return jwt.encode(
        payload,
        secret_key,
        algorithm=algorithm
    )