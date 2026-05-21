"""
反馈服务 - 用户反馈收集与处理
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.log import ConversationLog

logger = logging.getLogger(__name__)


class FeedbackService:
    """反馈服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_feedback(
        self,
        session_id: str,
        log_id: str,
        feedback: str,
        comment: Optional[str] = None,
    ):
        """记录用户反馈"""
        result = await self.db.execute(
            select(ConversationLog).where(ConversationLog.log_id == log_id)
        )
        log = result.scalar_one_or_none()

        if log:
            log.user_feedback = feedback
            await self.db.flush()
            logger.info(f"用户反馈已记录: session={session_id}, feedback={feedback}")
        else:
            logger.warning(f"未找到对话日志: log_id={log_id}")
