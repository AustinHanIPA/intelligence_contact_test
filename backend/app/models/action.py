"""
候选动作模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, Float, DateTime, Boolean, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CandidateAction(Base):
    """候选动作配置表"""
    __tablename__ = "candidate_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    action_type: Mapped[str] = mapped_column(String(50))  # faq_answer, tool_call, form, button, human_transfer
    intent: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    required_fields: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="low")
    estimated_resolution_rate: Mapped[float] = mapped_column(Float, default=0.5)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    need_human: Mapped[bool] = mapped_column(Boolean, default=False)
    tool_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    user_message_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    business_constraints: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_action_intent", "intent"),
        Index("idx_action_type", "action_type"),
    )
