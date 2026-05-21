"""
回复生成服务
根据选择的动作、知识证据和工具结果，生成自然客服回复
支持 LLM 生成（优先） + 模板兜底
"""
import json
import logging
from typing import List, Dict, Any, Optional

from app.models.session import CustomerSession
from app.schemas.chat import ChatResponse, ActionButton, MessageType
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

# 语气模板
TONE_TEMPLATES = {
    "apologetic": "非常抱歉给您带来了不便。",
    "empathetic": "我理解您的心情，",
    "professional": "",
    "warm": "您好！",
}

# 情绪对应的语气
EMOTION_TONE_MAP = {
    "angry": "apologetic",
    "anxious": "empathetic",
    "disappointed": "apologetic",
    "neutral": "professional",
    "positive": "warm",
}


class ResponseGenerator:
    """回复生成服务"""

    async def generate(
        self,
        intent: str,
        emotion: str,
        selected_action: Optional[Dict[str, Any]],
        knowledge: List[Dict[str, Any]],
        context: Dict[str, Any],
        tool_results: Optional[Dict[str, Any]],
        scored_actions: List[Dict[str, Any]] = None,
        user_message: str = "",
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ChatResponse:
        """
        生成最终客服回复
        策略：优先LLM生成，失败时回退到模板
        """
        session_id = context.get("session_info", {}).get("session_id", "")

        if not selected_action:
            return self._generate_fallback_response(session_id, emotion)

        action_type = selected_action.get("action_type")

        if action_type == "human_transfer":
            return self._generate_handoff_response(session_id, emotion)

        # 尝试LLM生成
        if llm_service.enabled and user_message:
            llm_response = await self._generate_with_llm(
                user_message=user_message,
                intent=intent,
                emotion=emotion,
                selected_action=selected_action,
                knowledge=knowledge,
                tool_results=tool_results,
                conversation_history=conversation_history,
            )
            if llm_response:
                buttons = self._generate_buttons(scored_actions)
                if action_type == "tool_call" and tool_results:
                    buttons = self._generate_follow_up_buttons(
                        selected_action.get("tool_name", ""), 
                        tool_results.get("data", {}),
                        scored_actions,
                    )
                return ChatResponse(
                    session_id=session_id,
                    message=llm_response,
                    message_type=MessageType.TEXT,
                    buttons=buttons if buttons else None,
                    metadata={"tool_result": tool_results.get("data") if tool_results else None},
                )

        # 回退到模板生成
        if action_type == "faq_answer":
            return self._generate_faq_response(
                session_id, selected_action, emotion, scored_actions
            )

        if action_type == "tool_call":
            return self._generate_tool_response(
                session_id, selected_action, tool_results, emotion, context, scored_actions
            )

        return self._generate_fallback_response(session_id, emotion)

    async def _generate_with_llm(
        self,
        user_message: str,
        intent: str,
        emotion: str,
        selected_action: Dict[str, Any],
        knowledge: List[Dict[str, Any]],
        tool_results: Optional[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]],
    ) -> Optional[str]:
        """使用LLM生成回复"""
        knowledge_text = ""
        if knowledge:
            knowledge_text = "\n".join(
                f"- {k.get('title', '')}: {k.get('content', '')}" 
                for k in knowledge[:3]
            )

        tool_text = ""
        if tool_results and tool_results.get("success"):
            tool_text = json.dumps(tool_results.get("data", {}), ensure_ascii=False, indent=2)

        return await llm_service.generate_response(
            user_message=user_message,
            intent=intent,
            emotion=emotion,
            knowledge_context=knowledge_text,
            tool_results=tool_text,
            conversation_history=conversation_history,
        )

    async def generate_from_tool_result(
        self,
        action_id: str,
        tool_results: Dict[str, Any],
        session: CustomerSession,
    ) -> ChatResponse:
        """根据工具执行结果生成回复"""
        if not tool_results or not tool_results.get("success"):
            return ChatResponse(
                session_id=session.session_id,
                message="抱歉，操作暂时无法完成。请稍后再试，或者我可以帮您转接人工客服。",
                message_type=MessageType.TEXT,
                buttons=[
                    ActionButton(label="重试", action=action_id, params={}),
                    ActionButton(label="转人工客服", action="handoff", params={}),
                ],
            )

        data = tool_results.get("data", {})
        message = data.get("message", "操作已完成。")

        return ChatResponse(
            session_id=session.session_id,
            message=message,
            message_type=MessageType.TEXT,
            metadata={"tool_result": data},
        )

    def _generate_faq_response(
        self,
        session_id: str,
        action: Dict[str, Any],
        emotion: str,
        scored_actions: List[Dict[str, Any]] = None,
    ) -> ChatResponse:
        """生成FAQ类型回复"""
        tone_prefix = TONE_TEMPLATES.get(EMOTION_TONE_MAP.get(emotion, "professional"), "")
        content = action.get("knowledge_content", action.get("user_message_template", ""))

        message = f"{tone_prefix}{content}"
        buttons = self._generate_buttons(scored_actions)

        return ChatResponse(
            session_id=session_id,
            message=message,
            message_type=MessageType.TEXT,
            buttons=buttons if buttons else None,
        )

    def _generate_tool_response(
        self,
        session_id: str,
        action: Dict[str, Any],
        tool_results: Optional[Dict[str, Any]],
        emotion: str,
        context: Dict[str, Any],
        scored_actions: List[Dict[str, Any]] = None,
    ) -> ChatResponse:
        """生成工具调用类型回复"""
        tone_prefix = TONE_TEMPLATES.get(EMOTION_TONE_MAP.get(emotion, "professional"), "")

        if not tool_results or not tool_results.get("success"):
            message = f"{tone_prefix}抱歉，系统暂时无法获取相关信息。请稍后再试，或者我可以帮您转接人工客服。"
            return ChatResponse(
                session_id=session_id,
                message=message,
                message_type=MessageType.TEXT,
                buttons=[
                    ActionButton(label="重试", action=action.get("action_id", ""), params={}),
                    ActionButton(label="转人工客服", action="handoff", params={}),
                ],
            )

        data = tool_results.get("data", {})
        tool_name = action.get("tool_name", "")
        message = self._format_tool_result(tool_name, data, tone_prefix, context)
        buttons = self._generate_follow_up_buttons(tool_name, data, scored_actions)

        return ChatResponse(
            session_id=session_id,
            message=message,
            message_type=MessageType.TEXT,
            buttons=buttons if buttons else None,
            metadata={"tool_result": data},
        )

    def _format_tool_result(
        self,
        tool_name: str,
        data: Dict[str, Any],
        tone_prefix: str,
        context: Dict[str, Any],
    ) -> str:
        """格式化工具调用结果为自然语言"""
        if tool_name == "order_query":
            return (
                f"{tone_prefix}我帮您查到了订单信息：\n\n"
                f"订单号：{data.get('order_id')}\n"
                f"商品：{data.get('product')}\n"
                f"状态：{data.get('status_text')}\n"
                f"金额：¥{data.get('amount')}\n"
                f"下单时间：{data.get('created_at')}"
            )

        elif tool_name == "logistics_query":
            timeline = data.get("timeline", [])
            latest = timeline[-1] if timeline else {}
            return (
                f"{tone_prefix}我帮您查到了物流信息：\n\n"
                f"快递公司：{data.get('carrier')}\n"
                f"运单号：{data.get('tracking_no')}\n"
                f"当前位置：{data.get('last_location')}\n"
                f"最新动态：{latest.get('desc', '暂无更新')}\n"
                f"物流已{data.get('stagnant_hours', 0)}小时未更新"
            )

        elif tool_name == "logistics_urge":
            return (
                f"{tone_prefix}已帮您提交物流催促申请。\n\n"
                f"催促单号：{data.get('urge_id')}\n"
                f"{data.get('message')}"
            )

        elif tool_name == "refund_check":
            eligible = data.get("eligible", False)
            if eligible:
                return (
                    f"{tone_prefix}经查询，您的订单符合退款条件：\n\n"
                    f"可退金额：¥{data.get('refund_amount')}\n"
                    f"退款方式：{data.get('refund_method')}\n"
                    f"预计到账：{data.get('estimated_days')}个工作日\n\n"
                    f"需要我帮您提交退款申请吗？"
                )
            else:
                return f"{tone_prefix}抱歉，经查询您的订单暂不符合退款条件。原因：{data.get('reason')}"

        elif tool_name == "refund_submit":
            return (
                f"{tone_prefix}退款申请已提交成功！\n\n"
                f"退款单号：{data.get('refund_id')}\n"
                f"{data.get('message')}"
            )

        elif tool_name == "ticket_create":
            return (
                f"{tone_prefix}工单已创建成功。\n\n"
                f"工单号：{data.get('ticket_id')}\n"
                f"{data.get('message')}"
            )

        else:
            return f"{tone_prefix}{data.get('message', '操作已完成。')}"

    def _generate_handoff_response(self, session_id: str, emotion: str) -> ChatResponse:
        """生成转人工回复"""
        tone_prefix = TONE_TEMPLATES.get(EMOTION_TONE_MAP.get(emotion, "professional"), "")
        message = f"{tone_prefix}好的，我现在为您转接人工客服。请稍等片刻，客服人员将尽快为您服务。"

        return ChatResponse(
            session_id=session_id,
            message=message,
            message_type=MessageType.SYSTEM,
            handoff=True,
        )

    def _generate_fallback_response(self, session_id: str, emotion: str) -> ChatResponse:
        """生成兜底回复"""
        tone_prefix = TONE_TEMPLATES.get(EMOTION_TONE_MAP.get(emotion, "professional"), "")
        message = (
            f"{tone_prefix}请问您需要什么帮助？我可以为您提供以下服务："
        )

        return ChatResponse(
            session_id=session_id,
            message=message,
            message_type=MessageType.TEXT,
            buttons=[
                ActionButton(label="查询订单", action="query_order", params={}),
                ActionButton(label="查询物流", action="query_logistics", params={}),
                ActionButton(label="申请退款", action="check_refund_eligibility", params={}),
                ActionButton(label="转人工客服", action="handoff", params={}),
            ],
        )

    def _generate_buttons(
        self, scored_actions: List[Dict[str, Any]] = None
    ) -> List[ActionButton]:
        """根据候选动作生成按钮"""
        buttons = []
        if not scored_actions:
            return buttons

        for action in scored_actions[1:4]:
            if action.get("action_type") == "human_transfer":
                buttons.append(
                    ActionButton(label="转人工客服", action="handoff", params={})
                )
            elif action.get("user_message_template"):
                label = action.get("name", "")[:10]
                buttons.append(
                    ActionButton(
                        label=label,
                        action=action.get("action_id", ""),
                        params={},
                    )
                )

        return buttons

    def _generate_follow_up_buttons(
        self,
        tool_name: str,
        data: Dict[str, Any],
        scored_actions: List[Dict[str, Any]] = None,
    ) -> List[ActionButton]:
        """生成后续操作按钮"""
        buttons = []

        if tool_name == "logistics_query":
            stagnant = data.get("stagnant_hours", 0)
            if stagnant >= 48:
                buttons.append(
                    ActionButton(label="帮我催促物流", action="urge_logistics", params={})
                )
            buttons.append(
                ActionButton(label="转人工客服", action="handoff", params={})
            )

        elif tool_name == "refund_check":
            if data.get("eligible"):
                buttons.append(
                    ActionButton(label="确认退款", action="submit_refund", params={})
                )
            buttons.append(
                ActionButton(label="转人工客服", action="handoff", params={})
            )

        elif tool_name == "order_query":
            buttons.append(
                ActionButton(label="查询物流", action="query_logistics", params={})
            )
            buttons.append(
                ActionButton(label="申请退款", action="check_refund_eligibility", params={})
            )

        if not buttons:
            buttons.append(
                ActionButton(label="还有其他问题", action="ask_clarification", params={})
            )
            buttons.append(
                ActionButton(label="转人工客服", action="handoff", params={})
            )

        return buttons
