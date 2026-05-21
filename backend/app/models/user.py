"""
用户模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100))
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    role: Mapped[str] = mapped_column(String(30), default="customer")  # customer, agent, supervisor, admin, operator
    member_level: Mapped[str] = mapped_column(String(20), default="normal")  # normal, vip, svip
    risk_tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
