"""
数据分析服务 - 仪表板和指标统计
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.log import ConversationLog, RuleLog, ToolCallLog
from app.models.session import CustomerSession

logger = logging.getLogger(__name__)


class AnalyticsService:
    """数据分析服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据"""
        # 总会话数
        total_sessions = await self.db.execute(
            select(func.count(CustomerSession.id))
        )
        # 活跃会话数
        active_sessions = await self.db.execute(
            select(func.count(CustomerSession.id)).where(
                CustomerSession.status == "active"
            )
        )
        # 转人工数
        handoff_sessions = await self.db.execute(
            select(func.count(CustomerSession.id)).where(
                CustomerSession.status == "handoff"
            )
        )
        # 总对话数
        total_conversations = await self.db.execute(
            select(func.count(ConversationLog.id))
        )

        return {
            "total_sessions": total_sessions.scalar() or 0,
            "active_sessions": active_sessions.scalar() or 0,
            "handoff_sessions": handoff_sessions.scalar() or 0,
            "total_conversations": total_conversations.scalar() or 0,
        }

    async def get_conversation_logs(
        self,
        session_id: Optional[str] = None,
        intent: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """获取对话日志"""
        stmt = select(ConversationLog)

        if session_id:
            stmt = stmt.where(ConversationLog.session_id == session_id)
        if intent:
            stmt = stmt.where(ConversationLog.detected_intent == intent)

        # 总数
        count_stmt = select(func.count(ConversationLog.id))
        if session_id:
            count_stmt = count_stmt.where(ConversationLog.session_id == session_id)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(ConversationLog.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        logs = result.scalars().all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "log_id": log.log_id,
                    "session_id": log.session_id,
                    "user_message": log.user_message,
                    "detected_intent": log.detected_intent,
                    "selected_action": log.selected_action,
                    "final_response": log.final_response,
                    "user_feedback": log.user_feedback,
                    "human_handoff": log.human_handoff,
                    "response_time_ms": log.response_time_ms,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
        }

    async def get_rule_logs(
        self,
        session_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """获取规则命中日志"""
        stmt = select(RuleLog)
        if session_id:
            stmt = stmt.where(RuleLog.session_id == session_id)

        stmt = stmt.order_by(RuleLog.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        logs = result.scalars().all()

        return {
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "log_id": log.log_id,
                    "session_id": log.session_id,
                    "rule_id": log.rule_id,
                    "rule_name": log.rule_name,
                    "matched": log.matched,
                    "blocked_action": log.blocked_action,
                    "reason": log.reason,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
        }

    async def get_tool_logs(
        self,
        session_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """获取工具调用日志"""
        stmt = select(ToolCallLog)
        if session_id:
            stmt = stmt.where(ToolCallLog.session_id == session_id)
        if tool_name:
            stmt = stmt.where(ToolCallLog.tool_name == tool_name)

        stmt = stmt.order_by(ToolCallLog.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        logs = result.scalars().all()

        return {
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "log_id": log.log_id,
                    "session_id": log.session_id,
                    "tool_name": log.tool_name,
                    "status": log.status,
                    "duration_ms": log.duration_ms,
                    "error_message": log.error_message,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
        }

    async def get_metrics(self, days: int = 7) -> Dict[str, Any]:
        """获取关键指标"""
        since = datetime.utcnow() - timedelta(days=days)

        # 总对话数
        total_convs = await self.db.execute(
            select(func.count(ConversationLog.id)).where(
                ConversationLog.created_at >= since
            )
        )

        # 转人工次数
        handoffs = await self.db.execute(
            select(func.count(ConversationLog.id)).where(
                and_(
                    ConversationLog.created_at >= since,
                    ConversationLog.human_handoff == True,
                )
            )
        )

        # 正面反馈
        good_feedback = await self.db.execute(
            select(func.count(ConversationLog.id)).where(
                and_(
                    ConversationLog.created_at >= since,
                    ConversationLog.user_feedback == "good",
                )
            )
        )

        # 平均响应时间
        avg_response = await self.db.execute(
            select(func.avg(ConversationLog.response_time_ms)).where(
                ConversationLog.created_at >= since
            )
        )

        total = total_convs.scalar() or 0
        handoff_count = handoffs.scalar() or 0
        good_count = good_feedback.scalar() or 0

        return {
            "period_days": days,
            "total_conversations": total,
            "handoff_count": handoff_count,
            "handoff_rate": round(handoff_count / max(total, 1) * 100, 2),
            "good_feedback_count": good_count,
            "satisfaction_rate": round(good_count / max(total, 1) * 100, 2),
            "avg_response_time_ms": round(avg_response.scalar() or 0, 0),
        }
