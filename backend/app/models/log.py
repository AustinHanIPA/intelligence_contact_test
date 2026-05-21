"""
日志模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, Boolean, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ConversationLog(Base):
    """对话日志表"""
    __tablename__ = "conversation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    log_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    session_id: Mapped[str] = mapped_column(String(100), index=True)
    user_message: Mapped[str] = mapped_column(Text)
    detected_intent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    detected_emotion: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    entities: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    retrieved_knowledge: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    candidate_actions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    filtered_actions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    selected_action: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    action_scores: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    final_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tool_results: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    user_feedback: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # good, bad, null
    human_handoff: Mapped[bool] = mapped_column(Boolean, default=False)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_conv_log_session", "session_id"),
        Index("idx_conv_log_intent", "detected_intent"),
    )


class RuleLog(Base):
    """规则命中日志表"""
    __tablename__ = "rule_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    log_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    session_id: Mapped[str] = mapped_column(String(100), index=True)
    rule_id: Mapped[str] = mapped_column(String(100))
    rule_name: Mapped[str] = mapped_column(String(200))
    matched: Mapped[bool] = mapped_column(Boolean, default=False)
    blocked_action: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_rule_log_session", "session_id"),
    )


class ToolCallLog(Base):
    """工具调用日志表"""
    __tablename__ = "tool_call_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    log_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    session_id: Mapped[str] = mapped_column(String(100), index=True)
    tool_name: Mapped[str] = mapped_column(String(100))
    request_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    response_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20))  # success, failed, timeout
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_tool_log_session", "session_id"),
        Index("idx_tool_log_name", "tool_name"),
    )
