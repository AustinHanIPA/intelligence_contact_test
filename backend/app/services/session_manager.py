"""
会话管理服务
管理用户会话的创建、更新和历史记录
"""
import uuid
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.session import CustomerSession
from app.models.log import ConversationLog

logger = logging.getLogger(__name__)


class SessionManager:
    """会话管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_session(
        self,
        session_id: Optional[str],
        user_id: str,
    ) -> CustomerSession:
        """获取或创建会话"""
        if session_id:
            session = await self.get_session(session_id)
            if session and session.status == "active":
                # 更新消息计数
                session.message_count = (session.message_count or 0) + 1
                await self.db.flush()
                return session

        # 创建新会话
        new_session = CustomerSession(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            status="active",
            message_count=1,
            verified=True,  # 简化版默认已验证
        )
        self.db.add(new_session)
        await self.db.flush()
        await self.db.refresh(new_session)
        return new_session

    async def get_session(self, session_id: str) -> Optional[CustomerSession]:
        """获取会话"""
        result = await self.db.execute(
            select(CustomerSession).where(CustomerSession.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def update_session(
        self,
        session: CustomerSession,
        updates: Dict[str, Any],
    ):
        """更新会话状态"""
        for key, value in updates.items():
            if hasattr(session, key):
                setattr(session, key, value)
        await self.db.flush()

    async def close_session(self, session_id: str):
        """关闭会话"""
        session = await self.get_session(session_id)
        if session:
            session.status = "closed"
            await self.db.flush()

    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[CustomerSession]:
        """获取会话列表"""
        stmt = select(CustomerSession)

        if user_id:
            stmt = stmt.where(CustomerSession.user_id == user_id)
        if status:
            stmt = stmt.where(CustomerSession.status == status)

        stmt = stmt.order_by(desc(CustomerSession.updated_at))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_conversation_history(
        self, session_id: str
    ) -> List[Dict[str, Any]]:
        """获取会话对话历史"""
        result = await self.db.execute(
            select(ConversationLog)
            .where(ConversationLog.session_id == session_id)
            .order_by(ConversationLog.created_at)
        )
        logs = result.scalars().all()

        history = []
        for log in logs:
            # 用户消息
            history.append({
                "role": "user",
                "content": log.user_message,
                "timestamp": log.created_at.isoformat() if log.created_at else None,
            })
            # 系统回复
            if log.final_response:
                history.append({
                    "role": "assistant",
                    "content": log.final_response,
                    "intent": log.detected_intent,
                    "timestamp": log.created_at.isoformat() if log.created_at else None,
                })

        return history
