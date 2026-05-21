"""
Scorer决策排序服务
对候选动作进行多维度打分，选择最合适的处理方案
"""
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# 默认打分权重
DEFAULT_WEIGHTS = {
    "resolution_rate": 0.35,
    "accuracy": 0.20,
    "satisfaction": 0.15,
    "speed": 0.10,
    "compliance_risk": -0.15,
    "cost": -0.05,
}

# 不同场景的权重配置
SCENE_WEIGHTS = {
    "shipping_delay": {
        "resolution_rate": 0.30,
        "accuracy": 0.15,
        "satisfaction": 0.25,  # 物流延迟场景更重视满意度
        "speed": 0.10,
        "compliance_risk": -0.15,
        "cost": -0.05,
    },
    "refund_request": {
        "resolution_rate": 0.25,
        "accuracy": 0.25,  # 退款场景更重视准确性
        "satisfaction": 0.15,
        "speed": 0.05,
        "compliance_risk": -0.25,  # 退款场景更重视合规风险
        "cost": -0.05,
    },
    "complaint": {
        "resolution_rate": 0.20,
        "accuracy": 0.15,
        "satisfaction": 0.35,  # 投诉场景最重视满意度
        "speed": 0.15,
        "compliance_risk": -0.10,
        "cost": -0.05,
    },
}


class ScorerService:
    """决策打分排序服务"""

    async def score(
        self,
        actions: List[Dict[str, Any]],
        context: Dict[str, Any],
        emotion: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        对候选动作进行多维度打分并排序
        """
        if not actions:
            return []

        # 获取当前场景的权重
        intent = context.get("session_info", {}).get("previous_intent", "")
        weights = SCENE_WEIGHTS.get(intent, DEFAULT_WEIGHTS)

        scored_actions = []
        for action in actions:
            score = self._calculate_score(action, context, emotion, weights)
            scored_actions.append({
                **action,
                "final_score": score,
                "score_breakdown": self._get_score_breakdown(action, context, emotion, weights),
            })

        # 按分数降序排序
        scored_actions.sort(key=lambda x: x["final_score"], reverse=True)

        return scored_actions

    def _calculate_score(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any],
        emotion: Optional[str],
        weights: Dict[str, float],
    ) -> float:
        """计算单个动作的综合分数"""
        # 解决概率
        resolution_rate = action.get("estimated_resolution_rate", 0.5)

        # 准确性（基于知识匹配度）
        accuracy = self._estimate_accuracy(action, context)

        # 满意度预测
        satisfaction = self._estimate_satisfaction(action, emotion)

        # 响应速度
        speed = self._estimate_speed(action)

        # 合规风险
        compliance_risk = self._estimate_compliance_risk(action)

        # 业务成本
        cost = self._normalize_cost(action.get("cost", 0))

        # 综合打分
        final_score = (
            weights["resolution_rate"] * resolution_rate
            + weights["accuracy"] * accuracy
            + weights["satisfaction"] * satisfaction
            + weights["speed"] * speed
            + weights["compliance_risk"] * compliance_risk
            + weights["cost"] * cost
        )

        return round(final_score, 4)

    def _estimate_accuracy(self, action: Dict[str, Any], context: Dict[str, Any]) -> float:
        """估算准确性"""
        # FAQ回答类型准确性较高
        if action.get("action_type") == "faq_answer" and action.get("knowledge_content"):
            return 0.85
        # 工具调用有真实数据支撑
        if action.get("action_type") == "tool_call":
            return 0.80
        # 人工转接默认高准确
        if action.get("action_type") == "human_transfer":
            return 0.95
        return 0.60

    def _estimate_satisfaction(self, action: Dict[str, Any], emotion: Optional[str]) -> float:
        """估算用户满意度"""
        base_satisfaction = 0.6

        # 人工转接在用户愤怒时满意度较高
        if action.get("action_type") == "human_transfer" and emotion == "angry":
            return 0.85

        # 直接解决问题的动作满意度较高
        if action.get("estimated_resolution_rate", 0) > 0.7:
            base_satisfaction += 0.2

        # 有补偿的动作满意度加分
        if "compensation" in action.get("action_id", ""):
            base_satisfaction += 0.15

        return min(base_satisfaction, 1.0)

    def _estimate_speed(self, action: Dict[str, Any]) -> float:
        """估算响应速度"""
        if action.get("action_type") == "faq_answer":
            return 0.95  # FAQ最快
        if action.get("action_type") == "tool_call":
            return 0.70  # 工具调用需要时间
        if action.get("action_type") == "human_transfer":
            return 0.30  # 转人工最慢
        return 0.60

    def _estimate_compliance_risk(self, action: Dict[str, Any]) -> float:
        """估算合规风险（越高越有风险）"""
        risk_map = {"low": 0.1, "medium": 0.5, "high": 0.9}
        return risk_map.get(action.get("risk_level", "low"), 0.3)

    def _normalize_cost(self, cost: float) -> float:
        """归一化成本（0-1，越高成本越大）"""
        # 假设最大成本为50
        return min(cost / 50.0, 1.0)

    def _get_score_breakdown(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any],
        emotion: Optional[str],
        weights: Dict[str, float],
    ) -> Dict[str, float]:
        """获取打分明细"""
        return {
            "resolution_rate": action.get("estimated_resolution_rate", 0.5),
            "accuracy": self._estimate_accuracy(action, context),
            "satisfaction": self._estimate_satisfaction(action, emotion),
            "speed": self._estimate_speed(action),
            "compliance_risk": self._estimate_compliance_risk(action),
            "cost": self._normalize_cost(action.get("cost", 0)),
        }
