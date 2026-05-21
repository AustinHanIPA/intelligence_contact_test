"""
NLU服务 - 意图识别、情绪识别、实体抽取
"""
import re
import logging
from typing import Dict, Any, Optional

from app.models.session import CustomerSession

logger = logging.getLogger(__name__)

# 意图关键词映射
INTENT_KEYWORDS = {
    "order_status": ["订单", "查订单", "订单状态", "我的订单", "下单", "买的"],
    "shipping_status": ["物流", "快递", "配送", "发货", "在哪", "到哪了"],
    "shipping_delay": ["没到", "还没收到", "延迟", "迟迟", "好几天", "一直没", "怎么还"],
    "refund_request": ["退款", "退钱", "还钱", "申请退款"],
    "return_request": ["退货", "退回", "换货", "退换"],
    "payment_failed": ["支付失败", "付款失败", "扣款", "没付成功", "支付异常"],
    "coupon_issue": ["优惠券", "折扣", "代金券", "抵扣", "优惠"],
    "account_login": ["登录", "登不上", "账号", "密码", "验证码"],
    "invoice_request": ["发票", "开票", "电子发票"],
    "complaint": ["投诉", "举报", "差评", "太差了", "垃圾"],
    "human_request": ["人工", "转人工", "客服", "真人", "人工客服"],
    "product_question": ["商品", "产品", "规格", "材质", "尺寸", "颜色"],
}

# 情绪关键词映射
EMOTION_KEYWORDS = {
    "angry": ["生气", "愤怒", "什么破", "垃圾", "骗子", "投诉", "举报", "怎么回事", "太离谱"],
    "anxious": ["着急", "急", "赶紧", "快点", "等不了", "明天就要"],
    "disappointed": ["失望", "不满", "差", "太差", "不满意", "不行"],
    "neutral": [],
    "positive": ["谢谢", "感谢", "好的", "可以", "明白"],
}


class NLUService:
    """自然语言理解服务"""

    async def analyze(
        self,
        message: str,
        session: Optional[CustomerSession] = None,
    ) -> Dict[str, Any]:
        """
        分析用户消息
        返回：意图、情绪、实体、置信度
        """
        # 意图识别
        intent, intent_confidence = self._detect_intent(message, session)

        # 情绪识别
        emotion = self._detect_emotion(message)

        # 实体抽取
        entities = self._extract_entities(message)

        # 综合置信度
        confidence = intent_confidence

        return {
            "intent": intent,
            "emotion": emotion,
            "entities": entities,
            "confidence": confidence,
        }

    def _detect_intent(
        self,
        message: str,
        session: Optional[CustomerSession] = None,
    ) -> tuple:
        """意图识别"""
        scores = {}

        for intent, keywords in INTENT_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in message:
                    score += 1
            if score > 0:
                scores[intent] = score / len(keywords)

        if not scores:
            # 如果没有匹配到任何意图，尝试使用上下文
            if session and session.current_intent:
                return session.current_intent, 0.4
            return "unknown", 0.2

        # 选择得分最高的意图
        best_intent = max(scores, key=scores.get)
        confidence = min(scores[best_intent] * 2, 0.95)  # 归一化到0-0.95

        # 多意图检测：如果有负面情绪关键词，附加情绪意图
        return best_intent, confidence

    def _detect_emotion(self, message: str) -> str:
        """情绪识别"""
        for emotion, keywords in EMOTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in message:
                    return emotion
        return "neutral"

    def _extract_entities(self, message: str) -> Dict[str, Any]:
        """实体抽取"""
        entities = {}

        # 订单号抽取（数字序列）
        order_patterns = [
            r'订单[号]?\s*[:：]?\s*(\d{6,20})',
            r'单号\s*[:：]?\s*(\d{6,20})',
            r'(?<!\d)(\d{10,20})(?!\d)',  # 10-20位纯数字
        ]
        for pattern in order_patterns:
            match = re.search(pattern, message)
            if match:
                entities["order_id"] = match.group(1)
                break

        # 金额抽取
        amount_patterns = [
            r'(\d+(?:\.\d{1,2})?)\s*[元块]',
            r'¥\s*(\d+(?:\.\d{1,2})?)',
            r'(\d+(?:\.\d{1,2})?)\s*(?:RMB|rmb)',
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, message)
            if match:
                entities["amount"] = float(match.group(1))
                break

        # 时间抽取
        time_patterns = [
            r'(\d{1,2})\s*[天日]前',
            r'(\d{1,2})\s*小时前',
            r'(昨天|前天|今天|大前天)',
        ]
        for pattern in time_patterns:
            match = re.search(pattern, message)
            if match:
                entities["time_ref"] = match.group(0)
                break

        # 商品名抽取（简化版）
        product_patterns = [
            r'买的(.{2,20}?)(?:怎么|还没|一直)',
            r'商品[名]?\s*[:：]?\s*(.{2,20})',
        ]
        for pattern in product_patterns:
            match = re.search(pattern, message)
            if match:
                entities["product"] = match.group(1).strip()
                break

        return entities

    async def generate_clarification(self, message: str, intent: str) -> str:
        """当置信度不足时生成澄清问题"""
        clarifications = {
            "unknown": "您好，请问您需要什么帮助？您可以选择以下服务：查询订单、查询物流、申请退款、申请退货，或者其他问题。",
            "order_status": "请问您是想查询订单状态吗？方便提供一下订单号吗？",
            "shipping_status": "请问您是想查询物流信息吗？请提供订单号，我帮您查询。",
            "refund_request": "请问您是想申请退款吗？方便告诉我是哪个订单以及退款原因吗？",
            "return_request": "请问您是想申请退货吗？请提供订单号和退货原因。",
        }
        return clarifications.get(intent, clarifications["unknown"])
