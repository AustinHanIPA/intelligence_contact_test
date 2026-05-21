"""
候选动作生成服务
根据意图、上下文和知识库生成多个可能的处理方案
"""
import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.action import CandidateAction

logger = logging.getLogger(__name__)

# 内置候选动作配置
BUILTIN_ACTIONS = {
    "order_status": [
        {
            "action_id": "query_order",
            "action_type": "tool_call",
            "name": "查询订单状态",
            "tool_name": "order_query",
            "required_fields": ["order_id"],
            "risk_level": "low",
            "estimated_resolution_rate": 0.85,
            "cost": 0.0,
            "need_human": False,
            "user_message_template": "我帮您查询一下订单状态。",
        },
        {
            "action_id": "show_order_list",
            "action_type": "faq_answer",
            "name": "展示订单查询入口",
            "tool_name": None,
            "required_fields": [],
            "risk_level": "low",
            "estimated_resolution_rate": 0.60,
            "cost": 0.0,
            "need_human": False,
            "user_message_template": "您可以在'我的订单'页面查看所有订单。",
        },
    ],
    "shipping_status": [
        {
            "action_id": "query_logistics",
            "action_type": "tool_call",
            "name": "查询物流状态",
            "tool_name": "logistics_query",
            "required_fields": ["order_id"],
            "risk_level": "low",
            "estimated_resolution_rate": 0.80,
            "cost": 0.0,
            "need_human": False,
            "user_message_template": "我帮您查询一下物流信息。",
        },
    ],
    "shipping_delay": [
        {
            "action_id": "explain_logistics_status",
            "action_type": "faq_answer",
            "name": "解释物流状态",
            "tool_name": None,
            "required_fields": ["order_id"],
            "risk_level": "low",
            "estimated_resolution_rate": 0.55,
            "cost": 0.0,
            "need_human": False,
            "user_message_template": "我帮您查看一下物流停滞的原因。",
        },
        {
            "action_id": "urge_logistics",
            "action_type": "tool_call",
            "name": "提交物流催促",
            "tool_name": "logistics_urge",
            "required_fields": ["order_id"],
            "risk_level": "low",
            "estimated_resolution_rate": 0.72,
            "cost": 0.1,
            "need_human": False,
            "user_message_template": "我可以先帮您提交一次物流催促。",
            "business_constraints": ["物流停滞超过48小时", "订单未签收"],
        },
        {
            "action_id": "offer_compensation",
            "action_type": "tool_call",
            "name": "申请补偿券",
            "tool_name": "coupon_issue",
            "required_fields": ["order_id", "user_id"],
            "risk_level": "medium",
            "estimated_resolution_rate": 0.80,
            "cost": 5.0,
            "need_human": False,
            "user_message_template": "考虑到给您带来的不便，我可以为您申请一张补偿券。",
            "business_constraints": ["物流停滞超过72小时"],
        },
        {
            "action_id": "create_complaint_ticket",
            "action_type": "tool_call",
            "name": "创建投诉工单",
            "tool_name": "ticket_create",
            "required_fields": ["order_id", "user_id"],
            "risk_level": "medium",
            "estimated_resolution_rate": 0.65,
            "cost": 1.0,
            "need_human": False,
            "user_message_template": "我为您创建一个投诉工单，会有专人跟进处理。",
        },
        {
            "action_id": "transfer_human",
            "action_type": "human_transfer",
            "name": "转人工客服",
            "tool_name": None,
            "required_fields": [],
            "risk_level": "low",
            "estimated_resolution_rate": 0.90,
            "cost": 10.0,
            "need_human": True,
            "user_message_template": "我为您转接人工客服。",
        },
    ],
    "refund_request": [
        {
            "action_id": "check_refund_eligibility",
            "action_type": "tool_call",
            "name": "检查退款资格",
            "tool_name": "refund_check",
            "required_fields": ["order_id"],
            "risk_level": "low",
            "estimated_resolution_rate": 0.70,
            "cost": 0.0,
            "need_human": False,
            "user_message_template": "我帮您确认一下退款资格。",
        },
        {
            "action_id": "submit_refund",
            "action_type": "tool_call",
            "name": "提交退款申请",
            "tool_name": "refund_submit",
            "required_fields": ["order_id", "reason"],
            "risk_level": "medium",
            "estimated_resolution_rate": 0.85,
            "cost": 0.5,
            "need_human": False,
            "user_message_template": "我帮您提交退款申请。",
            "business_constraints": ["退款金额不超过5000", "符合退款条件"],
        },
        {
            "action_id": "transfer_human_refund",
            "action_type": "human_transfer",
            "name": "转人工处理退款",
            "tool_name": None,
            "required_fields": [],
            "risk_level": "low",
            "estimated_resolution_rate": 0.90,
            "cost": 10.0,
            "need_human": True,
            "user_message_template": "退款需要人工审核，我为您转接专员。",
        },
    ],
    "return_request": [
        {
            "action_id": "check_return_eligibility",
            "action_type": "tool_call",
            "name": "检查退货资格",
            "tool_name": "return_check",
            "required_fields": ["order_id"],
            "risk_level": "low",
            "estimated_resolution_rate": 0.70,
            "cost": 0.0,
            "need_human": False,
            "user_message_template": "我帮您确认是否符合退货条件。",
        },
        {
            "action_id": "submit_return",
            "action_type": "tool_call",
            "name": "提交退货申请",
            "tool_name": "return_submit",
            "required_fields": ["order_id", "reason"],
            "risk_level": "medium",
            "estimated_resolution_rate": 0.80,
            "cost": 1.0,
            "need_human": False,
            "user_message_template": "我帮您提交退货申请。",
        },
    ],
    "human_request": [
        {
            "action_id": "direct_transfer",
            "action_type": "human_transfer",
            "name": "直接转人工",
            "tool_name": None,
            "required_fields": [],
            "risk_level": "low",
            "estimated_resolution_rate": 0.90,
            "cost": 10.0,
            "need_human": True,
            "user_message_template": "好的，我现在为您转接人工客服。",
        },
    ],
}

# 通用候选动作（所有意图都可使用）
COMMON_ACTIONS = [
    {
        "action_id": "ask_clarification",
        "action_type": "faq_answer",
        "name": "询问澄清",
        "tool_name": None,
        "required_fields": [],
        "risk_level": "low",
        "estimated_resolution_rate": 0.30,
        "cost": 0.0,
        "need_human": False,
    },
    {
        "action_id": "transfer_human_fallback",
        "action_type": "human_transfer",
        "name": "兜底转人工",
        "tool_name": None,
        "required_fields": [],
        "risk_level": "low",
        "estimated_resolution_rate": 0.85,
        "cost": 10.0,
        "need_human": True,
        "user_message_template": "如果我没能帮到您，可以为您转接人工客服。",
    },
]


class CandidateService:
    """候选动作生成服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate(
        self,
        intent: str,
        context: Dict[str, Any],
        knowledge: List[Dict[str, Any]],
        entities: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        根据意图和上下文生成候选动作
        """
        candidates = []

        # 1. 从内置配置获取意图对应的候选动作
        intent_actions = BUILTIN_ACTIONS.get(intent, [])
        candidates.extend(intent_actions)

        # 2. 从数据库加载自定义候选动作
        db_actions = await self._load_db_actions(intent)
        candidates.extend(db_actions)

        # 3. 如果知识库有强证据FAQ，添加FAQ回答动作
        for k in knowledge:
            if k.get("type") == "faq" and k.get("score", 0) > 0.7:
                candidates.append({
                    "action_id": f"faq_answer_{k['knowledge_id']}",
                    "action_type": "faq_answer",
                    "name": f"FAQ回答: {k['title']}",
                    "tool_name": None,
                    "required_fields": [],
                    "risk_level": "low",
                    "estimated_resolution_rate": 0.75,
                    "cost": 0.0,
                    "need_human": False,
                    "knowledge_content": k["content"],
                    "forbidden_claims": k.get("forbidden_claims"),
                })

        # 4. 添加通用候选动作
        candidates.extend(COMMON_ACTIONS)

        # 5. 过滤缺少必要字段的动作
        candidates = self._filter_by_required_fields(candidates, entities, context)

        return candidates

    async def enrich(
        self,
        candidates: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        补充候选动作的实时信息
        例如：订单状态、退款资格、物流停滞时间等
        """
        logistics_info = context.get("logistics_info")
        order_info = context.get("order_info")

        for candidate in candidates:
            # 补充物流停滞时间
            if candidate.get("action_id") == "urge_logistics" and logistics_info:
                candidate["context_data"] = {
                    "stagnant_hours": logistics_info.get("stagnant_hours", 0),
                    "last_location": logistics_info.get("last_location"),
                }

            # 补充退款相关信息
            if "refund" in candidate.get("action_id", "") and order_info:
                candidate["context_data"] = {
                    "amount": order_info.get("amount", 0),
                    "order_status": order_info.get("status"),
                }

        return candidates

    async def _load_db_actions(self, intent: str) -> List[Dict[str, Any]]:
        """从数据库加载候选动作"""
        try:
            result = await self.db.execute(
                select(CandidateAction).where(
                    CandidateAction.intent == intent,
                    CandidateAction.enabled == True,
                )
            )
            actions = result.scalars().all()
            return [
                {
                    "action_id": a.action_id,
                    "action_type": a.action_type,
                    "name": a.name,
                    "tool_name": a.tool_name,
                    "required_fields": a.required_fields or [],
                    "risk_level": a.risk_level,
                    "estimated_resolution_rate": a.estimated_resolution_rate,
                    "cost": a.cost,
                    "need_human": a.need_human,
                    "user_message_template": a.user_message_template,
                    "business_constraints": a.business_constraints,
                }
                for a in actions
            ]
        except Exception as e:
            logger.error(f"加载数据库候选动作失败: {str(e)}")
            return []

    def _filter_by_required_fields(
        self,
        candidates: List[Dict[str, Any]],
        entities: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """过滤缺少必要字段的候选动作"""
        available_fields = set(entities.keys())
        if context.get("order_info"):
            available_fields.update(context["order_info"].keys())
        if context.get("user_info"):
            available_fields.update(context["user_info"].keys())

        filtered = []
        for candidate in candidates:
            required = set(candidate.get("required_fields", []))
            if required.issubset(available_fields) or not required:
                filtered.append(candidate)
            else:
                # 缺少字段但仍保留，标记为需要追问
                candidate["missing_fields"] = list(required - available_fields)
                filtered.append(candidate)

        return filtered
