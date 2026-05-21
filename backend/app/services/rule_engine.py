"""
规则引擎 - 候选动作过滤和安全控制
判断候选动作是否允许执行，防止违规、错误或高风险行为
"""
import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import CustomerSession
from app.models.log import RuleLog

logger = logging.getLogger(__name__)


class Rule:
    """规则基类"""

    def __init__(self, rule_id: str, name: str, priority: int = 0):
        self.rule_id = rule_id
        self.name = name
        self.priority = priority

    def evaluate(
        self, action: Dict[str, Any], context: Dict[str, Any], session: CustomerSession
    ) -> Dict[str, Any]:
        """
        评估规则
        返回: {"passed": bool, "reason": str}
        """
        raise NotImplementedError


class AuthVerificationRule(Rule):
    """身份验证规则：未登录用户不能查看敏感信息"""

    def __init__(self):
        super().__init__("rule_auth_001", "身份验证规则", priority=100)

    def evaluate(self, action, context, session):
        user_info = context.get("user_info", {})
        if not user_info.get("verified", False):
            sensitive_actions = ["query_order", "submit_refund", "submit_return"]
            if action.get("action_id") in sensitive_actions:
                return {"passed": False, "reason": "用户身份未验证，禁止展示敏感信息"}
        return {"passed": True, "reason": ""}


class RefundAmountRule(Rule):
    """退款金额规则：高金额退款必须人工审核"""

    def __init__(self):
        super().__init__("rule_refund_001", "高金额退款审核规则", priority=90)

    def evaluate(self, action, context, session):
        if action.get("action_id") == "submit_refund":
            order_info = context.get("order_info", {})
            amount = order_info.get("amount", 0)
            if amount > 5000:
                return {
                    "passed": False,
                    "reason": f"退款金额{amount}元超过5000元阈值，需人工审核",
                    "force_handoff": True,
                }
        return {"passed": True, "reason": ""}


class LogisticsUrgeRule(Rule):
    """物流催促规则：停滞不足48小时不允许催促"""

    def __init__(self):
        super().__init__("rule_logistics_001", "物流催促时间规则", priority=80)

    def evaluate(self, action, context, session):
        if action.get("action_id") == "urge_logistics":
            logistics_info = context.get("logistics_info", {})
            stagnant_hours = logistics_info.get("stagnant_hours", 0)
            if stagnant_hours < 48:
                return {
                    "passed": False,
                    "reason": f"物流停滞{stagnant_hours}小时，未满48小时不允许催促",
                }
        return {"passed": True, "reason": ""}


class CompensationRule(Rule):
    """补偿规则：停滞不足72小时不允许发放补偿券"""

    def __init__(self):
        super().__init__("rule_compensation_001", "补偿券发放规则", priority=80)

    def evaluate(self, action, context, session):
        if action.get("action_id") == "offer_compensation":
            logistics_info = context.get("logistics_info", {})
            stagnant_hours = logistics_info.get("stagnant_hours", 0)
            if stagnant_hours < 72:
                return {
                    "passed": False,
                    "reason": f"物流停滞{stagnant_hours}小时，未满72小时不允许发放补偿券",
                }
        return {"passed": True, "reason": ""}


class EmotionEscalationRule(Rule):
    """情绪升级规则：用户强烈负面情绪优先转人工"""

    def __init__(self):
        super().__init__("rule_emotion_001", "情绪升级规则", priority=95)

    def evaluate(self, action, context, session):
        emotion = session.emotion
        message_count = session.message_count or 0
        if emotion == "angry" and message_count >= 3:
            # 用户连续多轮且情绪愤怒，建议转人工
            return {
                "passed": True,
                "reason": "",
                "suggest_handoff": True,
            }
        return {"passed": True, "reason": ""}


class ComplaintCountRule(Rule):
    """连续投诉规则：连续投诉>=3次优先转人工"""

    def __init__(self):
        super().__init__("rule_complaint_001", "连续投诉转人工规则", priority=95)

    def evaluate(self, action, context, session):
        risk_info = context.get("risk_info", {})
        complaint_count = risk_info.get("complaint_count", 0)
        if complaint_count >= 3:
            return {
                "passed": True,
                "reason": "",
                "force_handoff": True,
                "handoff_reason": f"用户连续投诉{complaint_count}次，强制转人工",
            }
        return {"passed": True, "reason": ""}


class VirtualProductRule(Rule):
    """虚拟商品规则：虚拟商品禁止普通退货流程"""

    def __init__(self):
        super().__init__("rule_virtual_001", "虚拟商品退货规则", priority=85)

    def evaluate(self, action, context, session):
        if action.get("action_id") in ["submit_return", "check_return_eligibility"]:
            order_info = context.get("order_info", {})
            product_category = order_info.get("product_category", "")
            if product_category == "virtual":
                return {
                    "passed": False,
                    "reason": "虚拟商品不支持退货流程",
                }
        return {"passed": True, "reason": ""}


class RuleEngine:
    """规则引擎"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.rules = self._load_rules()

    def _load_rules(self) -> List[Rule]:
        """加载所有规则"""
        rules = [
            AuthVerificationRule(),
            RefundAmountRule(),
            LogisticsUrgeRule(),
            CompensationRule(),
            EmotionEscalationRule(),
            ComplaintCountRule(),
            VirtualProductRule(),
        ]
        # 按优先级排序（高优先级先执行）
        rules.sort(key=lambda r: r.priority, reverse=True)
        return rules

    async def filter_actions(
        self,
        candidates: List[Dict[str, Any]],
        context: Dict[str, Any],
        session: CustomerSession,
    ) -> Dict[str, Any]:
        """
        对所有候选动作执行规则过滤
        返回：允许的动作列表、被阻止的动作列表、是否需要强制转人工
        """
        allowed = []
        blocked = []
        force_handoff = False
        handoff_reason = ""

        for action in candidates:
            action_blocked = False

            for rule in self.rules:
                result = rule.evaluate(action, context, session)

                # 记录规则命中日志
                if not result["passed"] or result.get("force_handoff"):
                    await self._log_rule(
                        session_id=session.session_id,
                        rule=rule,
                        matched=True,
                        blocked_action=action.get("action_id"),
                        reason=result.get("reason", ""),
                    )

                if not result["passed"]:
                    blocked.append({
                        **action,
                        "blocked_by": rule.rule_id,
                        "blocked_reason": result["reason"],
                    })
                    action_blocked = True
                    break

                if result.get("force_handoff"):
                    force_handoff = True
                    handoff_reason = result.get("handoff_reason", "规则触发强制转人工")

            if not action_blocked:
                allowed.append(action)

        return {
            "allowed": allowed,
            "blocked": blocked,
            "force_handoff": force_handoff,
            "handoff_reason": handoff_reason,
        }

    async def _log_rule(
        self,
        session_id: str,
        rule: Rule,
        matched: bool,
        blocked_action: Optional[str],
        reason: str,
    ):
        """记录规则命中日志"""
        try:
            import uuid
            log = RuleLog(
                log_id=str(uuid.uuid4()),
                session_id=session_id,
                rule_id=rule.rule_id,
                rule_name=rule.name,
                matched=matched,
                blocked_action=blocked_action,
                reason=reason,
            )
            self.db.add(log)
            await self.db.flush()
        except Exception as e:
            logger.error(f"记录规则日志失败: {str(e)}")
