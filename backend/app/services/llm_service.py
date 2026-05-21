"""
LLM服务 - OpenAI API 集成
支持意图识别增强、回复生成、对话摘要等
"""
import json
import logging
from typing import Optional, List, Dict, Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """LLM对话服务（OpenAI兼容接口）"""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL
        self.model = settings.LLM_MODEL
        self.enabled = bool(self.api_key)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        json_mode: bool = False,
    ) -> Optional[str]:
        """调用LLM生成回复"""
        if not self.enabled:
            return None

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]

        except httpx.TimeoutException:
            logger.warning("LLM API调用超时")
            return None
        except Exception as e:
            logger.error(f"LLM API调用失败: {str(e)}")
            return None

    async def analyze_intent(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """使用LLM增强意图识别"""
        system_prompt = """你是一个客服意图分析系统。根据用户消息判断意图、情绪和关键实体。
请返回JSON格式：
{
  "intent": "意图标签",
  "emotion": "情绪标签",
  "entities": {"key": "value"},
  "confidence": 0.0-1.0
}

可用的意图标签：order_status, shipping_status, shipping_delay, refund_request, return_request, 
payment_failed, coupon_issue, account_login, invoice_request, complaint, human_request, product_question, unknown

可用的情绪标签：angry, anxious, disappointed, neutral, positive"""

        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history[-4:])
        messages.append({"role": "user", "content": user_message})

        result = await self.chat_completion(messages, temperature=0.3, json_mode=True)
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.warning(f"LLM意图分析返回非JSON: {result}")
        return None

    async def generate_response(
        self,
        user_message: str,
        intent: str,
        emotion: str,
        knowledge_context: str = "",
        tool_results: str = "",
        conversation_history: List[Dict[str, str]] = None,
    ) -> Optional[str]:
        """使用LLM生成自然语言客服回复"""
        system_prompt = f"""你是一个专业、友好的智能客服助手。请根据以下信息生成回复：

用户意图：{intent}
用户情绪：{emotion}
{"知识库参考：" + knowledge_context if knowledge_context else ""}
{"工具调用结果：" + tool_results if tool_results else ""}

回复要求：
1. 语气友好、专业
2. 如果用户情绪为angry/anxious，先表示理解和歉意
3. 根据知识库和工具结果给出准确信息
4. 不要编造不存在的信息
5. 回复简洁明了，通常2-4句话
6. 使用中文回复"""

        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history[-6:])
        messages.append({"role": "user", "content": user_message})

        return await self.chat_completion(messages, temperature=0.7, max_tokens=512)

    async def generate_summary(
        self,
        conversation_history: List[Dict[str, str]],
    ) -> Optional[str]:
        """生成对话摘要（用于转人工时）"""
        system_prompt = """请为以下客服对话生成简短摘要，包括：
1. 用户主要问题
2. 已采取的措施
3. 未解决的问题
4. 建议后续处理方式
摘要控制在200字以内。"""

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history[-10:])
        messages.append({"role": "user", "content": "请生成对话摘要"})

        return await self.chat_completion(messages, temperature=0.3, max_tokens=300)


# 全局单例
llm_service = LLMService()
