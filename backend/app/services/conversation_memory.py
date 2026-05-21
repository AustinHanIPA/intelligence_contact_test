"""
对话记忆服务 - 多轮对话上下文管理
基于滑动窗口 + Redis 缓存实现高效的多轮对话上下文
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import timedelta

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)

# 对话窗口大小配置
MAX_WINDOW_SIZE = 10  # 最多保留最近10轮对话
CONTEXT_TTL = timedelta(hours=2)  # 上下文缓存过期时间


class ConversationMemory:
    """对话记忆管理器"""

    def __init__(self):
        self._redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> redis.Redis:
        """获取 Redis 连接（延迟初始化）"""
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                )
                await self._redis.ping()
            except Exception as e:
                logger.warning(f"Redis连接失败，使用内存缓存: {str(e)}")
                self._redis = None
        return self._redis

    def _session_key(self, session_id: str) -> str:
        """生成Redis key"""
        return f"conv_memory:{session_id}"

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """添加一条消息到对话记忆"""
        message = {
            "role": role,
            "content": content,
        }
        if metadata:
            message["metadata"] = metadata

        r = await self._get_redis()
        if r:
            try:
                key = self._session_key(session_id)
                await r.rpush(key, json.dumps(message, ensure_ascii=False))
                # 保持窗口大小
                await r.ltrim(key, -MAX_WINDOW_SIZE * 2, -1)
                # 刷新过期时间
                await r.expire(key, int(CONTEXT_TTL.total_seconds()))
            except Exception as e:
                logger.error(f"Redis写入失败: {str(e)}")
        else:
            # 降级：不缓存（依赖数据库历史）
            pass

    async def get_history(
        self,
        session_id: str,
        max_messages: int = None,
    ) -> List[Dict[str, str]]:
        """获取对话历史（用于LLM上下文）"""
        if max_messages is None:
            max_messages = MAX_WINDOW_SIZE * 2

        r = await self._get_redis()
        if r:
            try:
                key = self._session_key(session_id)
                messages = await r.lrange(key, -max_messages, -1)
                return [json.loads(m) for m in messages]
            except Exception as e:
                logger.error(f"Redis读取失败: {str(e)}")

        return []

    async def get_formatted_history(
        self,
        session_id: str,
        max_turns: int = 5,
    ) -> List[Dict[str, str]]:
        """获取格式化的历史记录（用于LLM messages参数）"""
        history = await self.get_history(session_id, max_turns * 2)
        # 只保留 role 和 content 字段
        return [{"role": m["role"], "content": m["content"]} for m in history]

    async def clear(self, session_id: str):
        """清空会话记忆"""
        r = await self._get_redis()
        if r:
            try:
                await r.delete(self._session_key(session_id))
            except Exception as e:
                logger.error(f"Redis删除失败: {str(e)}")

    async def get_summary_context(self, session_id: str) -> str:
        """获取简短的历史摘要（用于上下文补充）"""
        history = await self.get_history(session_id, 6)
        if not history:
            return ""

        parts = []
        for msg in history[-6:]:
            role_label = "用户" if msg["role"] == "user" else "客服"
            content = msg["content"][:80]
            parts.append(f"{role_label}: {content}")

        return "\n".join(parts)


# 全局单例
conversation_memory = ConversationMemory()
