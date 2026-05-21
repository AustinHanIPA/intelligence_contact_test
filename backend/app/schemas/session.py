"""
会话相关Schema
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class SessionResponse(BaseModel):
    """会话响应"""
    session_id: str
    user_id: str
    current_intent: Optional[str] = None
    emotion: Optional[str] = None
    slots: Optional[Dict[str, Any]] = None
    status: str
    message_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class HandoffRequest(BaseModel):
    """转人工请求"""
    session_id: str
    reason: Optional[str] = None


class HandoffSummary(BaseModel):
    """转人工摘要"""
    session_id: str
    user_id: str
    summary: str
    completed_actions: list
    suggested_actions: list
    user_emotion: Optional[str] = None
    order_info: Optional[Dict[str, Any]] = None
