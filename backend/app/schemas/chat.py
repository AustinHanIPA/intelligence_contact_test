"""
聊天相关Schema
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class MessageType(str, Enum):
    TEXT = "text"
    BUTTON = "button"
    FORM = "form"
    CARD = "card"
    SYSTEM = "system"


class ChatRequest(BaseModel):
    """用户聊天请求"""
    session_id: Optional[str] = None
    user_id: str
    message: str
    metadata: Optional[Dict[str, Any]] = None


class ActionButton(BaseModel):
    """操作按钮"""
    label: str
    action: str
    params: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """系统聊天回复"""
    session_id: str
    message: str
    message_type: MessageType = MessageType.TEXT
    buttons: Optional[List[ActionButton]] = None
    metadata: Optional[Dict[str, Any]] = None
    intent: Optional[str] = None
    emotion: Optional[str] = None
    confidence: Optional[float] = None
    handoff: bool = False
    timestamp: datetime = datetime.utcnow()


class FeedbackRequest(BaseModel):
    """用户反馈"""
    session_id: str
    log_id: str
    feedback: str  # good, bad
    comment: Optional[str] = None
