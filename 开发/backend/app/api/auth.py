import json
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import uuid4

import httpx
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.dependencies import require_user, verify_csrf
from app.models import AuditLog, MCPSettings, ProjectSubmission, RefreshToken, User
from app.schemas import (
    LoginRequest,
    Message,
    NotificationOut,
    PasswordChange,
    ProfileUpdate,
    SocialAccountsUpdate,
    UserCreate,
    UserOut,
)
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


@router.patch("/social-accounts", response_model=UserOut, dependencies=[Depends(verify_csrf)])
async def update_social_accounts(
    payload: SocialAccountsUpdate,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    user.github_username = (
        payload.github_username.strip().lstrip("@") if payload.github_username else None
    )
    user.gitee_username = (
        payload.gitee_username.strip().lstrip("@") if payload.gitee_username else None
    )
    await session.commit()
    await session.refresh(user)
    return user


@router.patch("/profile", response_model=UserOut, dependencies=[Depends(verify_csrf)])
async def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    user.display_name = payload.display_name.strip()
    user.real_name = payload.real_name.strip() if payload.real_name else None
    user.avatar_url = payload.avatar_url.strip() if payload.avatar_url else None
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/avatar", response_model=UserOut, dependencies=[Depends(verify_csrf)])
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    allowed = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    suffix = allowed.get(file.content_type or "")
    if not suffix:
        raise HTTPException(status_code=415, detail="头像仅支持 JPG、PNG、WEBP 或 GIF")
    content = await file.read(2 * 1024 * 1024 + 1)
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="头像文件不能超过 2MB")
    folder = settings.data_dir / "media" / "avatars"
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{user.id}-{uuid4().hex}{suffix}"
    (folder / filename).write_bytes(content)
    user.avatar_url = f"/media/avatars/{filename}"
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/mcp-token", response_model=Message, dependencies=[Depends(verify_csrf)])
async def create_mcp_token(
    user: User = Depends(require_user), session: AsyncSession = Depends(get_session)
) -> Message:
    token = new_refresh_token()
    user.mcp_token_hash = hash_refresh_token(token)
    await session.commit()
    return Message(message=token)


@router.get("/notifications", response_model=list[NotificationOut])
async def notifications(
    user: User = Depends(require_user), session: AsyncSession = Depends(get_session)
) -> list[NotificationOut]:
    projects = await session.scalars(
        select(ProjectSubmission)
        .where(ProjectSubmission.owner_id == user.id)
        .order_by(ProjectSubmission.updated_at.desc())
        .limit(20)
    )
    labels = {
        "draft": "草稿",
        "pending_review": "审核中",
        "published": "已发布",
        "rejected": "需要修改",
        "archived": "已归档",
    }
    return [
        NotificationOut(
            id=f"project-{item.id}",
            title=f"项目「{item.name}」{labels.get(item.status.value, item.status.value)}",
            message=item.review_note or "项目状态有更新，点击进入我的项目查看详情。",
            created_at=item.updated_at,
        )
        for item in projects
    ]


@router.get("/oauth/{provider}/start")
async def oauth_start(
    provider: str,
    response: Response,
    request: Request,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    if provider not in {"github", "gitee"}:
        raise HTTPException(404, "不支持的账号平台")
    settings_row = await session.get(MCPSettings, 1)
    client_id = getattr(settings_row, f"{provider}_client_id", None) if settings_row else None
    client_secret = (
        getattr(settings_row, f"{provider}_client_secret", None) if settings_row else None
    )
    if not client_id or not client_secret:
        raise HTTPException(503, f"管理员尚未配置 {provider} OAuth 凭据")
    state = secrets.token_urlsafe(32)
    callback = f"{settings.frontend_url}/api/v1/auth/oauth/{provider}/callback"
    if provider == "github":
        target = "https://github.com/login/oauth/authorize?" + urlencode(
            {
                "client_id": client_id,
                "redirect_uri": callback,
                "scope": "read:user user:email",
                "state": state,
            }
        )
    else:
        target = "https://gitee.com/oauth/authorize?" + urlencode(
            {
                "client_id": client_id,
                "redirect_uri": callback,
                "response_type": "code",
                "scope": "user_info",
                "state": state,
            }
        )
    result = RedirectResponse(target, status_code=307)
    result.set_cookie(
        "oauth_state",
        state,
        httponly=True,
        samesite="lax",
        max_age=600,
        secure=settings.cookie_secure,
        path="/",
    )
    return result


@router.get("/oauth/{provider}/callback", name="oauth_callback")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    request: Request,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
    oauth_state: str | None = Cookie(default=None),
):
    if (
        provider not in {"github", "gitee"}
        or not oauth_state
        or not secrets.compare_digest(state, oauth_state)
    ):
        raise HTTPException(400, "OAuth 状态无效，请重新绑定")
    settings_row = await session.get(MCPSettings, 1)
    client_id = getattr(settings_row, f"{provider}_client_id")
    client_secret = getattr(settings_row, f"{provider}_client_secret")
    async with httpx.AsyncClient(timeout=12) as client:
        if provider == "github":
            token_res = await client.post(
                "https://github.com/login/oauth/access_token",
                data={"client_id": client_id, "client_secret": client_secret, "code": code},
                headers={"Accept": "application/json"},
            )
            token = token_res.json().get("access_token")
            profile = (
                await client.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                    },
                )
            ).json()
            username = profile.get("login")
        else:
            token_res = await client.post(
                "https://gitee.com/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": client_id,
                    "redirect_uri": f"{settings.frontend_url}/api/v1/auth/oauth/{provider}/callback",
                    "client_secret": client_secret,
                },
            )
            token = token_res.json().get("access_token")
            profile = (
                await client.get("https://gitee.com/api/v5/user", params={"access_token": token})
            ).json()
            username = profile.get("login") or profile.get("name")
    if not username:
        raise HTTPException(502, "无法从官方接口读取账号信息")
    if provider == "github":
        user.github_username = username
    else:
        user.gitee_username = username
    await session.commit()
    result = RedirectResponse(f"{settings.frontend_url}/profile", status_code=303)
    result.delete_cookie("oauth_state", path="/")
    return result


@router.post("/password", response_model=Message, dependencies=[Depends(verify_csrf)])
async def change_password(
    payload: PasswordChange,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> Message:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码不正确")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与当前密码相同")
    user.password_hash = hash_password(payload.new_password)
    session.add(
        AuditLog(
            actor_id=user.id,
            action="auth.password.change",
            target_type="user",
            target_id=str(user.id),
            detail=json.dumps({"changed": True}, ensure_ascii=False),
        )
    )
    await session.commit()
    return Message(message="密码已修改")
