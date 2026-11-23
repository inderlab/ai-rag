import logging
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User, Video

ALGORITHM = "HS256"

log = logging.getLogger(__name__)


@lru_cache
def secret() -> str:
    if len(settings.JWT_SECRET) >= 32:
        return settings.JWT_SECRET
    log.warning("JWT_SECRET is missing or shorter than 32 chars; using a random one for this run")
    return secrets.token_urlsafe(48)


bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], hashed.encode())
    except ValueError:
        return False


def create_token(user: User, minutes: int | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=minutes or settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user.id), "email": user.email, "exp": expire}
    return jwt.encode(payload, secret(), algorithm=ALGORITHM)


def user_from_token(session: Session, token: str) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, secret(), algorithms=[ALGORITHM])
        user = session.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError) as e:
        raise unauthorized from e
    if user is None:
        raise unauthorized
    return user


def optional_user(
    session: Annotated[Session, Depends(get_db)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    token: Annotated[str | None, Query(include_in_schema=False)] = None,
) -> User | None:
    raw = creds.credentials if creds else token
    if raw:
        return user_from_token(session, raw)
    if settings.AUTH_REQUIRED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return None


def required_user(user: Annotated[User | None, Depends(optional_user)]) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User | None, Depends(optional_user)]
LoggedInUser = Annotated[User, Depends(required_user)]


def can_see(video: Video, user: User | None) -> bool:
    return video.user_id is None or (user is not None and video.user_id == user.id)


def scope_id(user: User | None) -> int:
    return user.id if user else 0
