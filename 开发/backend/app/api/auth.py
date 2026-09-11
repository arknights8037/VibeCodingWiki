from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.dependencies import require_user, verify_csrf
from app.models import RefreshToken, User
from app.schemas import LoginRequest, Message, UserCreate, UserOut
from app.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_csrf_token,
    new_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def set_auth_cookies(response: Response, user: User, refresh_value: str, csrf_value: str) -> None:
    common = {"secure": settings.cookie_secure, "samesite": "lax", "path": "/"}
    response.set_cookie(
        "access_token",
        create_access_token(user.id, user.role.value),
        httponly=True,
        max_age=settings.access_token_minutes * 60,
        **common,
    )
    response.set_cookie(
        "refresh_token",
        refresh_value,
        httponly=True,
        max_age=settings.refresh_token_days * 86400,
        **common,
    )
    response.set_cookie(
        "csrf_token",
        csrf_value,
        httponly=False,
        max_age=settings.refresh_token_days * 86400,
        **common,
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, session: AsyncSession = Depends(get_session)) -> User:
    email = payload.email.lower()
    if await session.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="邮箱已注册")
    user = User(
        email=email,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/login", response_model=UserOut)
async def login(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> User:
    user = await session.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    refresh_value = new_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_value),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
    )
    await session.commit()
    set_auth_cookies(response, user, refresh_value, new_csrf_token())
    return user


@router.post("/refresh", response_model=UserOut, dependencies=[Depends(verify_csrf)])
async def refresh_session(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not refresh_token:
        raise HTTPException(status_code=401, detail="刷新令牌缺失")
    token = await session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(refresh_token),
            RefreshToken.revoked_at.is_(None),
        )
    )
    if not token:
        raise HTTPException(status_code=401, detail="刷新令牌无效")
    expiry = token.expires_at if token.expires_at.tzinfo else token.expires_at.replace(tzinfo=UTC)
    if expiry <= datetime.now(UTC):
        raise HTTPException(status_code=401, detail="刷新令牌已过期")
    user = await session.get(User, token.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不可用")
    token.revoked_at = datetime.now(UTC)
    next_refresh = new_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(next_refresh),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
    )
    await session.commit()
    set_auth_cookies(response, user, next_refresh, new_csrf_token())
    return user


@router.post("/logout", response_model=Message, dependencies=[Depends(verify_csrf)])
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
) -> Message:
    if refresh_token:
        token = await session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(refresh_token))
        )
        if token:
            token.revoked_at = datetime.now(UTC)
            await session.commit()
    for key in ("access_token", "refresh_token", "csrf_token"):
        response.delete_cookie(key, path="/")
    return Message(message="已退出")


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(require_user)) -> User:
    return user
