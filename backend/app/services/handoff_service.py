"""
人工客服协同服务
处理转人工逻辑，生成对话摘要
"""
import logging
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.session import CustomerSession
from app.models.log import ConversationLog
from app.schemas.session import HandoffSummary
from app.services.session_manager import SessionManager

logger = logging.getLogger(__name__)


class HandoffService:
    """人工客服协同服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_manager = SessionManager(db)

    async def create_handoff(
        self,
        session_id: str,
        reason: Optional[str] = None,
    ) -> HandoffSummary:
        """
        创建转人工记录，生成对话摘要
        """
        session = await self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("会话不存在")

        # 更新会话状态
        await self.session_manager.update_session(session, {
            "status": "handoff",
            "handoff_required": True,
            "handoff_reason": reason or "用户请求转人工",
        })

        # 获取对话历史
        history = await self._get_session_logs(session_id)

        # 生成摘要
        summary = self._generate_summary(session, history, reason)

        return summary

    async def _get_session_logs(self, session_id: str):
        """获取会话日志"""
        result = await self.db.execute(
            select(ConversationLog)
            .where(ConversationLog.session_id == session_id)
            .order_by(ConversationLog.created_at)
        )
        return result.scalars().all()

    def _generate_summary(
        self,
        session: CustomerSession,
        logs: list,
        reason: Optional[str],
    ) -> HandoffSummary:
        """
        生成人工接入摘要
        包含：用户问题、已完成动作、建议处理方式
        """
        # 提取用户消息摘要
        user_messages = [log.user_message for log in logs if log.user_message]
        problem_summary = "；".join(user_messages[-3:]) if user_messages else "未知问题"

        # 提取已完成动作
        completed_actions = []
        for log in logs:
            if log.selected_action:
                completed_actions.append(log.selected_action)

        # 生成建议
        suggestions = self._generate_suggestions(session, logs)

        # 构建摘要文本
        summary_text = (
            f"用户问题摘要：{problem_summary}\n"
            f"当前意图：{session.current_intent or '未知'}\n"
            f"用户情绪：{session.emotion or '正常'}\n"
            f"对话轮次：{session.message_count or 0}\n"
            f"转人工原因：{reason or '用户请求'}"
        )

        return HandoffSummary(
            session_id=session.session_id,
            user_id=session.user_id,
            summary=summary_text,
            completed_actions=completed_actions,
            suggested_actions=suggestions,
            user_emotion=session.emotion,
            order_info=session.context.get("order_info") if session.context else None,
        )

    def _generate_suggestions(self, session: CustomerSession, logs: list) -> list:
        """生成人工客服处理建议"""
        suggestions = []

        if session.emotion == "angry":
            suggestions.append("优先安抚用户情绪")

        if session.current_intent == "refund_request":
            suggestions.append("核实退款条件后根据规则处理退款")

        if session.current_intent == "shipping_delay":
            suggestions.append("可根据规则申请补偿券或提交异常物流工单")

        if not suggestions:
            suggestions.append("了解用户具体需求后提供帮助")

        return suggestions
