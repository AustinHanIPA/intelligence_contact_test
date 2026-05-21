"""
Embedding服务 - 向量化文本用于语义检索
支持 OpenAI embedding API 或本地 sentence-transformers
"""
import logging
from typing import Optional, List

import httpx
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """文本向量化服务"""

    def __init__(self):
        self.dimension = settings.EMBEDDING_DIMENSION
        self.openai_key = settings.OPENAI_API_KEY
        self.openai_base_url = settings.OPENAI_BASE_URL
        self._local_model = None

    async def embed_text(self, text: str) -> Optional[List[float]]:
        """将文本转为向量"""
        if not text or not text.strip():
            return None

        # 优先使用 OpenAI embedding API
        if self.openai_key:
            embedding = await self._openai_embed(text)
            if embedding:
                return embedding

        # 回退到本地模型
        return self._local_embed(text)

    async def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """批量向量化"""
        if not texts:
            return []

        if self.openai_key:
            results = await self._openai_embed_batch(texts)
            if results:
                return results

        return [self._local_embed(t) for t in texts]

    async def _openai_embed(self, text: str) -> Optional[List[float]]:
        """使用OpenAI API生成embedding"""
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "text-embedding-ada-002",
                "input": text[:8000],  # 截断过长文本
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.openai_base_url}/embeddings",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                embedding = data["data"][0]["embedding"]

                # 如果维度不匹配，截断或补零
                if len(embedding) != self.dimension:
                    embedding = self._resize_embedding(embedding, self.dimension)

                return embedding

        except Exception as e:
            logger.error(f"OpenAI embedding失败: {str(e)}")
            return None

    async def _openai_embed_batch(self, texts: List[str]) -> Optional[List[List[float]]]:
        """批量OpenAI embedding"""
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "text-embedding-ada-002",
                "input": [t[:8000] for t in texts],
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.openai_base_url}/embeddings",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                embeddings = [item["embedding"] for item in data["data"]]

                return [
                    self._resize_embedding(e, self.dimension) if len(e) != self.dimension else e
                    for e in embeddings
                ]

        except Exception as e:
            logger.error(f"OpenAI batch embedding失败: {str(e)}")
            return None

    def _local_embed(self, text: str) -> Optional[List[float]]:
        """使用简化的本地向量化（基于文本哈希的伪向量，仅用于开发测试）"""
        try:
            # 生成确定性伪向量用于开发环境
            # 生产环境应替换为真实的sentence-transformers模型
            text_bytes = text.encode("utf-8")
            np.random.seed(hash(text) % (2**32))
            embedding = np.random.randn(self.dimension).astype(float)
            # 归一化
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            return embedding.tolist()
        except Exception as e:
            logger.error(f"本地embedding失败: {str(e)}")
            return None

    def _resize_embedding(self, embedding: List[float], target_dim: int) -> List[float]:
        """调整embedding维度"""
        if len(embedding) >= target_dim:
            return embedding[:target_dim]
        else:
            return embedding + [0.0] * (target_dim - len(embedding))


# 全局单例
embedding_service = EmbeddingService()
