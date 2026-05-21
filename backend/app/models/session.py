"""
会话模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, Boolean, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CustomerSession(Base):
    """用户会话表"""
    __tablename__ = "customer_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    current_intent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    emotion: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    slots: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # 上下文信息
    last_action: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pending_action: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    handoff_required: Mapped[bool] = mapped_column(Boolean, default=False)
    handoff_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, closed, handoff
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_session_user", "user_id"),
        Index("idx_session_status", "status"),
    )
