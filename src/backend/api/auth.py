"""Local administrator authentication for QUANTUM TRADER V1."""

import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field

security = HTTPBearer(auto_error=False)
auth_router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
_password_hasher = PasswordHasher()


def validate_auth_settings(settings: Any) -> None:
    """Fail closed unless signing and administrator credentials are provisioned."""
    secret = settings.secret_key
    if (
        not isinstance(secret, str)
        or len(secret) < 32
        or secret.strip().lower() in {
            "your-secret-key-here-change-in-production",
            "change-me",
            "your-secret-key",
            "placeholder",
            "secret",
        }
    ):
        raise ValueError(
            "Authentication requires SECRET_KEY with at least 32 characters "
            "of non-placeholder secret material."
        )

    if settings.algorithm != "HS256":
        raise ValueError("Authentication currently supports only HS256.")

    if not isinstance(settings.admin_username, str) or not settings.admin_username.strip():
        raise ValueError("ADMIN_USERNAME must be configured before starting the application.")

    password_hash = settings.admin_password_hash
    if not isinstance(password_hash, str) or not password_hash.startswith("$argon2id$"):
        raise ValueError(
            "ADMIN_PASSWORD_HASH must contain an Argon2id password hash. "
            "Generate one with: python -m src.backend.utils.create_admin"
        )

    if settings.access_token_expire_minutes < 1 or settings.access_token_expire_minutes > 1440:
        raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be between 1 and 1440.")


def verify_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, str]:
    """Validate a signed, unexpired access token for protected REST routes."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    settings = request.app.state.config.settings
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=["HS256"],
            options={"require_exp": True, "require_iat": True, "require_sub": True},
        )
        username = payload.get("username")
        subject = payload.get("sub")
        role = payload.get("role")
        if (
            not isinstance(username, str)
            or not isinstance(subject, str)
            or not hmac.compare_digest(username.encode('utf-8'), settings.admin_username.encode('utf-8'))
            or not hmac.compare_digest(subject.encode('utf-8'), settings.admin_username.encode('utf-8'))
            or role != "admin"
            or payload.get("token_type") != "access"
        ):
            raise unauthorized
        return {"user_id": subject, "username": username, "role": role}
    except (JWTError, TypeError, ValueError):
        raise unauthorized


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)


class AuthUser(BaseModel):
    id: str
    username: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUser


@auth_router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, request: Request) -> LoginResponse:
    """Authenticate the single provisioned local administrator."""
    settings = request.app.state.config.settings
    username_matches = hmac.compare_digest(
        payload.username.encode('utf-8'), settings.admin_username.encode('utf-8')
    )

    try:
        password_matches = _password_hasher.verify(
            settings.admin_password_hash, payload.password
        )
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        password_matches = False

    if not username_matches or not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = datetime.now(timezone.utc)
    expires_in = settings.access_token_expire_minutes * 60
    claims = {
        "sub": settings.admin_username,
        "username": settings.admin_username,
        "role": "admin",
        "token_type": "access",
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(claims, settings.secret_key, algorithm="HS256")
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=AuthUser(
            id=settings.admin_username,
            username=settings.admin_username,
            role="admin",
        ),
    )


@auth_router.get("/me", response_model=AuthUser)
async def current_user(user: dict[str, str] = Depends(verify_token)) -> AuthUser:
    """Return the identity represented by the validated bearer token."""
    return AuthUser(
        id=user["user_id"],
        username=user["username"],
        role=user["role"],
    )
