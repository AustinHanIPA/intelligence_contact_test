"""
工具执行器 - 业务API调用
负责调用订单、物流、退款等业务系统API
"""
import uuid
import time
import logging
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log import ToolCallLog
from app.config import settings

logger = logging.getLogger(__name__)


# 模拟业务API响应
MOCK_TOOL_RESPONSES = {
    "order_query": {
        "123456": {
            "success": True,
            "data": {
                "order_id": "123456",
                "product": "Nintendo Switch",
                "status": "in_transit",
                "status_text": "运输中",
                "amount": 2199.00,
                "created_at": "2025-01-10 14:30:00",
                "payment_status": "paid",
                "seller": "任天堂官方旗舰店",
            },
        },
        "789012": {
            "success": True,
            "data": {
                "order_id": "789012",
                "product": "Sony WH-1000XM5",
                "status": "delivered",
                "status_text": "已签收",
                "amount": 1999.00,
                "created_at": "2025-01-05 10:00:00",
                "payment_status": "paid",
                "seller": "索尼官方旗舰店",
            },
        },
    },
    "logistics_query": {
        "123456": {
            "success": True,
            "data": {
                "order_id": "123456",
                "carrier": "顺丰快递",
                "tracking_no": "SF1234567890",
                "status": "in_transit",
                "last_location": "东京中转站",
                "last_update_time": "2025-01-13 08:00:00",
                "stagnant_hours": 52,
                "timeline": [
                    {"time": "2025-01-10 16:00", "desc": "卖家已发货"},
                    {"time": "2025-01-11 10:00", "desc": "到达上海集散中心"},
                    {"time": "2025-01-12 08:00", "desc": "到达东京中转站"},
                    {"time": "2025-01-13 08:00", "desc": "东京中转站处理中"},
                ],
            },
        },
    },
    "logistics_urge": {
        "default": {
            "success": True,
            "data": {
                "urge_id": "URG_20250115_001",
                "status": "submitted",
                "message": "催促申请已提交，物流方将在24小时内更新配送状态",
            },
        },
    },
    "refund_check": {
        "123456": {
            "success": True,
            "data": {
                "eligible": True,
                "reason": "订单在可退款期限内",
                "refund_amount": 2199.00,
                "refund_method": "原路退回",
                "estimated_days": 3,
            },
        },
        "789012": {
            "success": True,
            "data": {
                "eligible": True,
                "reason": "已签收7天内可退",
                "refund_amount": 1999.00,
                "refund_method": "原路退回",
                "estimated_days": 5,
            },
        },
    },
    "refund_submit": {
        "default": {
            "success": True,
            "data": {
                "refund_id": "RF_20250115_001",
                "status": "processing",
                "message": "退款申请已提交，预计1-3个工作日处理完成",
            },
        },
    },
    "return_check": {
        "789012": {
            "success": True,
            "data": {
                "eligible": True,
                "reason": "签收7天内，符合退货条件",
                "return_address": "上海市浦东新区退货中心",
                "need_shipping_fee": False,
            },
        },
    },
    "return_submit": {
        "default": {
            "success": True,
            "data": {
                "return_id": "RT_20250115_001",
                "status": "pending_ship",
                "message": "退货申请已通过，请在7天内寄回商品",
                "return_address": "上海市浦东新区退货中心",
            },
        },
    },
    "ticket_create": {
        "default": {
            "success": True,
            "data": {
                "ticket_id": "TK_20250115_001",
                "status": "open",
                "message": "工单已创建，客服专员将在2小时内跟进处理",
            },
        },
    },
    "coupon_issue": {
        "default": {
            "success": True,
            "data": {
                "coupon_id": "CP_20250115_001",
                "amount": 10.00,
                "type": "满减券",
                "message": "已为您发放10元满减优惠券",
            },
        },
    },
}


class ToolExecutor:
    """工具执行器"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(
        self,
        tool_name: str,
        params: Dict[str, Any],
        session_id: str,
    ) -> Dict[str, Any]:
        """
        执行工具调用
        所有工具调用都必须：
        1. 经过权限校验
        2. 记录日志
        3. 有超时控制
        4. 失败时不编造结果
        """
        start_time = time.time()
        log_id = str(uuid.uuid4())

        try:
            # 执行工具调用（当前使用模拟数据）
            result = await self._call_tool(tool_name, params)

            duration = int((time.time() - start_time) * 1000)

            # 记录成功日志
            await self._log_tool_call(
                log_id=log_id,
                session_id=session_id,
                tool_name=tool_name,
                params=params,
                result=result,
                status="success",
                duration=duration,
            )

            return result

        except TimeoutError:
            duration = int((time.time() - start_time) * 1000)
            error_result = {
                "success": False,
                "error": "tool_timeout",
                "message": "工具调用超时，请稍后重试",
            }
            await self._log_tool_call(
                log_id=log_id,
                session_id=session_id,
                tool_name=tool_name,
                params=params,
                result=error_result,
                status="timeout",
                duration=duration,
                error="调用超时",
            )
            return error_result

        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            error_result = {
                "success": False,
                "error": "tool_error",
                "message": "系统暂时无法处理该请求，请稍后重试或联系人工客服",
            }
            await self._log_tool_call(
                log_id=log_id,
                session_id=session_id,
                tool_name=tool_name,
                params=params,
                result=error_result,
                status="failed",
                duration=duration,
                error=str(e),
            )
            logger.error(f"工具调用失败: tool={tool_name}, error={str(e)}")
            return error_result

    async def _call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """实际调用工具（模拟版）"""
        tool_data = MOCK_TOOL_RESPONSES.get(tool_name, {})

        # 尝试按参数匹配
        order_id = params.get("order_id", "")
        if order_id in tool_data:
            return tool_data[order_id]
        elif "default" in tool_data:
            return tool_data["default"]
        else:
            return {
                "success": False,
                "error": "not_found",
                "message": f"未找到相关信息",
            }

    async def _log_tool_call(
        self,
        log_id: str,
        session_id: str,
        tool_name: str,
        params: Dict[str, Any],
        result: Dict[str, Any],
        status: str,
        duration: int,
        error: str = None,
    ):
        """记录工具调用日志"""
        try:
            log = ToolCallLog(
                log_id=log_id,
                session_id=session_id,
                tool_name=tool_name,
                request_params=params,
                response_result=result,
                status=status,
                error_message=error,
                duration_ms=duration,
            )
            self.db.add(log)
            await self.db.flush()
        except Exception as e:
            logger.error(f"记录工具调用日志失败: {str(e)}")
