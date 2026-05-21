"""
对话编排器 - 核心流程控制
负责串联整个对话处理流程：
意图识别 → 上下文补全 → 知识检索 → 候选生成 → 规则过滤 → 打分排序 → 回复生成
"""
import uuid
import time
import logging
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import CustomerSession
from app.models.log import ConversationLog
from app.schemas.chat import ChatResponse, ActionButton, MessageType
from app.services.nlu_service import NLUService
from app.services.context_service import ContextService
from app.services.knowledge_service import KnowledgeService
from app.services.candidate_service import CandidateService
from app.services.rule_engine import RuleEngine
from app.services.scorer_service import ScorerService
from app.services.response_generator import ResponseGenerator
from app.services.tool_executor import ToolExecutor
from app.services.session_manager import SessionManager
from app.services.conversation_memory import conversation_memory

logger = logging.getLogger(__name__)


class ConversationOrchestrator:
    """对话编排器 - 决策系统核心"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.nlu = NLUService()
        self.context_service = ContextService(db)
        self.knowledge_service = KnowledgeService(db)
        self.candidate_service = CandidateService(db)
        self.rule_engine = RuleEngine(db)
        self.scorer = ScorerService()
        self.response_generator = ResponseGenerator()
        self.tool_executor = ToolExecutor(db)
        self.session_manager = SessionManager(db)

    async def process_message(
        self,
        session: CustomerSession,
        user_message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatResponse:
        """
        处理用户消息的核心流程
        """
        start_time = time.time()
        log_id = str(uuid.uuid4())

        try:
            # Step 0: 获取对话历史上下文
            conversation_history = await conversation_memory.get_formatted_history(
                session.session_id, max_turns=5
            )

            # 记录用户消息到记忆
            await conversation_memory.add_message(
                session.session_id, "user", user_message
            )

            # Step 1: 意图识别 & 实体抽取 & 情绪识别
            nlu_result = await self.nlu.analyze(
                user_message, session, conversation_history
            )
            intent = nlu_result["intent"]
            emotion = nlu_result["emotion"]
            entities = nlu_result["entities"]
            confidence = nlu_result["confidence"]

            logger.info(f"NLU结果: intent={intent}, emotion={emotion}, confidence={confidence}, source={nlu_result.get('source')}")

            # 更新会话状态
            await self.session_manager.update_session(session, {
                "current_intent": intent,
                "emotion": emotion,
                "slots": {**(session.slots or {}), **entities},
            })

            # Step 2: 低置信度处理 - 触发澄清问题
            if confidence < 0.6:
                clarification = await self.nlu.generate_clarification(user_message, intent)
                await conversation_memory.add_message(
                    session.session_id, "assistant", clarification
                )
                return ChatResponse(
                    session_id=session.session_id,
                    message=clarification,
                    message_type=MessageType.TEXT,
                    intent=intent,
                    emotion=emotion,
                    confidence=confidence,
                )

            # Step 3: 上下文补全
            context = await self.context_service.hydrate(
                user_id=session.user_id,
                session=session,
                intent=intent,
                entities=entities,
            )

            # Step 4: 知识检索
            knowledge_results = await self.knowledge_service.search(
                query=user_message,
                intent=intent,
                context=context,
            )

            # Step 5: 候选动作生成
            candidates = await self.candidate_service.generate(
                intent=intent,
                context=context,
                knowledge=knowledge_results,
                entities=entities,
            )

            # Step 6: 候选信息补全（通过工具调用补充实时数据）
            enriched_candidates = await self.candidate_service.enrich(
                candidates=candidates,
                context=context,
            )

            # Step 7: 规则过滤
            filtered_result = await self.rule_engine.filter_actions(
                candidates=enriched_candidates,
                context=context,
                session=session,
            )
            allowed_actions = filtered_result["allowed"]
            blocked_actions = filtered_result["blocked"]

            # Step 8: 检查是否需要强制转人工
            if filtered_result.get("force_handoff"):
                response = await self._handle_handoff(
                    session=session,
                    reason=filtered_result.get("handoff_reason", "规则触发转人工"),
                    context=context,
                )
                await conversation_memory.add_message(
                    session.session_id, "assistant", response.message
                )
                return response

            # Step 9: 多维打分排序
            scored_actions = await self.scorer.score(
                actions=allowed_actions,
                context=context,
                emotion=emotion,
            )

            # Step 10: 选择最佳动作
            selected_action = scored_actions[0] if scored_actions else None

            # Step 11: 执行工具调用（如果需要）
            tool_results = None
            if selected_action and selected_action.get("action_type") == "tool_call":
                tool_results = await self.tool_executor.execute(
                    tool_name=selected_action["tool_name"],
                    params=self._build_tool_params(selected_action, context, entities),
                    session_id=session.session_id,
                )

            # Step 12: 生成最终回复
            response = await self.response_generator.generate(
                intent=intent,
                emotion=emotion,
                selected_action=selected_action,
                knowledge=knowledge_results,
                context=context,
                tool_results=tool_results,
                scored_actions=scored_actions[:3],
                user_message=user_message,
                conversation_history=conversation_history,
            )

            # 记录回复到记忆
            await conversation_memory.add_message(
                session.session_id, "assistant", response.message
            )

            # Step 13: 记录对话日志
            response_time = int((time.time() - start_time) * 1000)
            await self._log_conversation(
                log_id=log_id,
                session=session,
                user_message=user_message,
                nlu_result=nlu_result,
                knowledge_results=knowledge_results,
                candidates=[c.get("action_id") for c in enriched_candidates],
                blocked=[b.get("action_id") for b in blocked_actions],
                selected=selected_action,
                scored_actions=scored_actions,
                response=response,
                tool_results=tool_results,
                response_time=response_time,
            )

            return response

        except Exception as e:
            logger.error(f"对话处理异常: {str(e)}", exc_info=True)
            # 降级处理：返回友好错误消息
            return ChatResponse(
                session_id=session.session_id,
                message="非常抱歉，系统暂时遇到了一些问题。请稍后再试，或者我可以帮您转接人工客服。",
                message_type=MessageType.TEXT,
                buttons=[
                    ActionButton(label="转人工客服", action="handoff", params={}),
                    ActionButton(label="重试", action="retry", params={}),
                ],
            )

    async def execute_action(
        self,
        session_id: str,
        action_id: str,
        params: Dict[str, Any],
    ) -> ChatResponse:
        """执行用户选择的动作"""
        session = await self.session_manager.get_session(session_id)
        if not session:
            return ChatResponse(
                session_id=session_id,
                message="会话已过期，请重新开始对话。",
                message_type=MessageType.TEXT,
            )

        if action_id == "handoff":
            return await self._handle_handoff(session, reason="用户主动请求转人工")

        # 执行具体动作
        tool_results = await self.tool_executor.execute(
            tool_name=action_id,
            params=params,
            session_id=session_id,
        )

        # 根据工具结果生成回复
        response = await self.response_generator.generate_from_tool_result(
            action_id=action_id,
            tool_results=tool_results,
            session=session,
        )

        # 记录到对话记忆
        await conversation_memory.add_message(
            session_id, "assistant", response.message
        )

        return response

    async def _handle_handoff(
        self,
        session: CustomerSession,
        reason: str,
        context: Dict[str, Any] = None,
    ) -> ChatResponse:
        """处理转人工"""
        await self.session_manager.update_session(session, {
            "status": "handoff",
            "handoff_required": True,
            "handoff_reason": reason,
        })

        return ChatResponse(
            session_id=session.session_id,
            message="好的，我现在为您转接人工客服。请稍等片刻，客服人员将尽快为您服务。",
            message_type=MessageType.SYSTEM,
            handoff=True,
            metadata={"reason": reason},
        )

    def _build_tool_params(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any],
        entities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """构建工具调用参数"""
        params = {}
        required_fields = action.get("required_fields", [])
        for field in required_fields:
            if field in entities:
                params[field] = entities[field]
            elif field in (context.get("order_info") or {}):
                params[field] = context["order_info"][field]
            elif field in (context.get("user_info") or {}):
                params[field] = context["user_info"][field]
        return params

    async def _log_conversation(self, **kwargs):
        """记录对话日志"""
        try:
            log = ConversationLog(
                log_id=kwargs["log_id"],
                session_id=kwargs["session"].session_id,
                user_message=kwargs["user_message"],
                detected_intent=kwargs["nlu_result"]["intent"],
                detected_emotion=kwargs["nlu_result"]["emotion"],
                entities=kwargs["nlu_result"]["entities"],
                retrieved_knowledge=[k.get("knowledge_id") for k in (kwargs["knowledge_results"] or [])],
                candidate_actions=kwargs["candidates"],
                filtered_actions=kwargs["blocked"],
                selected_action=kwargs["selected"]["action_id"] if kwargs["selected"] else None,
                action_scores=kwargs["scored_actions"],
                final_response=kwargs["response"].message if kwargs["response"] else None,
                tool_results=kwargs["tool_results"],
                response_time_ms=kwargs["response_time"],
            )
            self.db.add(log)
            await self.db.flush()
        except Exception as e:
            logger.error(f"记录对话日志失败: {str(e)}")
