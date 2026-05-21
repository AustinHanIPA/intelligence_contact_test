"""
NLU服务 - 意图识别、情绪识别、实体抽取
支持规则匹配（基线）+ LLM增强（可选）
"""
import re
import logging
from typing import Dict, Any, Optional, List

from app.models.session import CustomerSession
from app.services.llm_service import llm_service

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
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        分析用户消息
        策略：优先使用LLM（若可用），否则回退到规则匹配
        """
        # 尝试LLM分析
        if llm_service.enabled:
            llm_result = await llm_service.analyze_intent(message, conversation_history)
            if llm_result and llm_result.get("intent"):
                # LLM结果与规则结果融合
                rule_intent, rule_confidence = self._detect_intent(message, session)
                rule_entities = self._extract_entities(message)

                # 合并实体（规则提取的实体通常更准确）
                merged_entities = {**(llm_result.get("entities") or {}), **rule_entities}

                return {
                    "intent": llm_result["intent"],
                    "emotion": llm_result.get("emotion", self._detect_emotion(message)),
                    "entities": merged_entities,
                    "confidence": llm_result.get("confidence", 0.85),
                    "source": "llm",
                }

        # 回退到规则匹配
        intent, intent_confidence = self._detect_intent(message, session)
        emotion = self._detect_emotion(message)
        entities = self._extract_entities(message)

        return {
            "intent": intent,
            "emotion": emotion,
            "entities": entities,
            "confidence": intent_confidence,
            "source": "rules",
        }

    def _detect_intent(
        self,
        message: str,
        session: Optional[CustomerSession] = None,
    ) -> tuple:
        """意图识别（规则匹配）"""
        scores = {}

        for intent, keywords in INTENT_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in message:
                    score += 1
            if score > 0:
                scores[intent] = score / len(keywords)

        if not scores:
            if session and session.current_intent:
                return session.current_intent, 0.4
            return "unknown", 0.2

        best_intent = max(scores, key=scores.get)
        confidence = min(scores[best_intent] * 2, 0.95)

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

        # 订单号抽取
        order_patterns = [
            r'订单[号]?\s*[:：]?\s*(\d{6,20})',
            r'单号\s*[:：]?\s*(\d{6,20})',
            r'(?<!\d)(\d{10,20})(?!\d)',
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

        # 商品名抽取
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
        # 尝试LLM生成
        if llm_service.enabled:
            prompt = f"用户说：{message}\n当前猜测意图：{intent}\n请生成一个简短的澄清问题帮助确认用户需求。"
            result = await llm_service.chat_completion(
                [{"role": "system", "content": "你是智能客服，需要向用户提出澄清问题确认需求。回复简短自然。"},
                 {"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=150,
            )
            if result:
                return result

        # 回退到模板
        clarifications = {
            "unknown": "您好，请问您需要什么帮助？您可以选择以下服务：查询订单、查询物流、申请退款、申请退货，或者其他问题。",
            "order_status": "请问您是想查询订单状态吗？方便提供一下订单号吗？",
            "shipping_status": "请问您是想查询物流信息吗？请提供订单号，我帮您查询。",
            "refund_request": "请问您是想申请退款吗？方便告诉我是哪个订单以及退款原因吗？",
            "return_request": "请问您是想申请退货吗？请提供订单号和退货原因。",
        }
        return clarifications.get(intent, clarifications["unknown"])
