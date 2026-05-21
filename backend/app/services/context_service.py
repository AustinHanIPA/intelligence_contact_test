"""
上下文补全服务
根据用户身份和会话信息，自动补全业务上下文
"""
import logging
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.session import CustomerSession
from app.models.user import User

logger = logging.getLogger(__name__)


# 模拟订单数据（实际环境会调用订单API）
MOCK_ORDERS = {
    "123456": {
        "order_id": "123456",
        "product": "Nintendo Switch",
        "status": "in_transit",
        "amount": 2199.00,
        "created_at": "2025-01-10",
        "payment_status": "paid",
    },
    "789012": {
        "order_id": "789012",
        "product": "Sony WH-1000XM5",
        "status": "delivered",
        "amount": 1999.00,
        "created_at": "2025-01-05",
        "payment_status": "paid",
    },
    "345678": {
        "order_id": "345678",
        "product": "Apple AirPods Pro",
        "status": "pending",
        "amount": 1499.00,
        "created_at": "2025-01-15",
        "payment_status": "paid",
    },
}

# 模拟物流数据
MOCK_LOGISTICS = {
    "123456": {
        "order_id": "123456",
        "carrier": "顺丰快递",
        "tracking_no": "SF1234567890",
        "status": "in_transit",
        "last_location": "东京中转站",
        "last_update": "48小时前",
        "stagnant_hours": 52,
    },
    "789012": {
        "order_id": "789012",
        "carrier": "京东物流",
        "tracking_no": "JD9876543210",
        "status": "delivered",
        "last_location": "已签收",
        "last_update": "3天前",
        "stagnant_hours": 0,
    },
}


class ContextService:
    """上下文补全服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def hydrate(
        self,
        user_id: str,
        session: CustomerSession,
        intent: str,
        entities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        补全上下文信息
        """
        context = {
            "user_info": await self._get_user_info(user_id),
            "session_info": {
                "session_id": session.session_id,
                "verified": session.verified,
                "message_count": session.message_count,
                "previous_intent": session.current_intent,
            },
            "order_info": None,
            "logistics_info": None,
            "risk_info": None,
        }

        # 根据意图补全相关信息
        order_id = entities.get("order_id") or self._get_recent_order_id(user_id)

        if intent in ["order_status", "shipping_status", "shipping_delay",
                      "refund_request", "return_request"]:
            if order_id:
                context["order_info"] = await self._get_order_info(order_id)

        if intent in ["shipping_status", "shipping_delay"]:
            if order_id:
                context["logistics_info"] = await self._get_logistics_info(order_id)

        # 风险标签
        context["risk_info"] = await self._get_risk_info(user_id)

        return context

    async def _get_user_info(self, user_id: str) -> Dict[str, Any]:
        """获取用户信息"""
        result = await self.db.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()

        if user:
            return {
                "user_id": user.user_id,
                "username": user.username,
                "member_level": user.member_level,
                "is_active": user.is_active,
                "verified": True,
            }

        # 默认用户信息
        return {
            "user_id": user_id,
            "username": "用户",
            "member_level": "normal",
            "is_active": True,
            "verified": False,
        }

    async def _get_order_info(self, order_id: str) -> Optional[Dict[str, Any]]:
        """获取订单信息（模拟）"""
        return MOCK_ORDERS.get(order_id)

    async def _get_logistics_info(self, order_id: str) -> Optional[Dict[str, Any]]:
        """获取物流信息（模拟）"""
        return MOCK_LOGISTICS.get(order_id)

    async def _get_risk_info(self, user_id: str) -> Dict[str, Any]:
        """获取风险信息"""
        return {
            "risk_level": "low",
            "complaint_count": 0,
            "fraud_flag": False,
        }

    def _get_recent_order_id(self, user_id: str) -> Optional[str]:
        """获取最近订单ID（模拟）"""
        # 在实际系统中会查询数据库
        return "123456"
