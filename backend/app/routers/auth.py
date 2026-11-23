from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import LoggedInUser, create_token, hash_password, verify_password
from app.config import settings
from app.db import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    name: str
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserOut


class AuthConfig(BaseModel):
    auth_required: bool


def user_out(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email)


def token_for(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_token(user),
        expires_in_minutes=settings.JWT_EXPIRE_MINUTES,
        user=user_out(user),
    )


@router.get("/config", response_model=AuthConfig)
def auth_config() -> AuthConfig:
    return AuthConfig(auth_required=settings.AUTH_REQUIRED)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, session: DbSession) -> TokenResponse:
    email = body.email.lower()
    if session.scalar(select(func.count()).select_from(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="This email is already registered")
    user = User(name=body.name.strip(), email=email, password_hash=hash_password(body.password))
    session.add(user)
    session.commit()
    return token_for(user)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, session: DbSession) -> TokenResponse:
    user = session.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong email or password")
    return token_for(user)


@router.get("/me", response_model=UserOut)
def me(user: LoggedInUser) -> UserOut:
    return user_out(user)
