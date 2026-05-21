"""
认证API - 登录、注册、token刷新
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.services.auth_service import (
    AuthService, create_access_token, decode_token
)

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: str


class UserInfoResponse(BaseModel):
    user_id: str
    username: str
    email: Optional[str] = None
    role: str
    member_level: str


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """获取当前登录用户（可选鉴权）"""
    if not token:
        return None

    payload = decode_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    auth_service = AuthService(db)
    return await auth_service.get_user_by_id(user_id)


async def require_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """强制要求用户登录"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """用户登录"""
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.user_id, "role": user.role})

    return TokenResponse(
        access_token=access_token,
        user_id=user.user_id,
        username=user.username,
        role=user.role,
    )


@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """用户注册"""
    auth_service = AuthService(db)

    # 检查用户名是否已存在
    from sqlalchemy import select
    from app.models.user import User
    existing = await db.execute(select(User).where(User.username == request.username))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    user = await auth_service.register_user(
        username=request.username,
        password=request.password,
        email=request.email,
    )

    access_token = create_access_token(data={"sub": user.user_id, "role": user.role})

    return TokenResponse(
        access_token=access_token,
        user_id=user.user_id,
        username=user.username,
        role=user.role,
    )


@router.get("/me", response_model=UserInfoResponse)
async def get_me(
    user=Depends(require_user),
):
    """获取当前用户信息"""
    return UserInfoResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        role=user.role,
        member_level=user.member_level,
    )
