"""
知识库服务 - 知识管理与检索
支持向量检索 + 关键词检索 + FAQ精确匹配
"""
import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_

from app.models.knowledge import KnowledgeChunk
from app.schemas.knowledge import (
    KnowledgeCreate, KnowledgeUpdate, KnowledgeResponse, KnowledgeListResponse
)

logger = logging.getLogger(__name__)

# 内置FAQ知识库（MVP阶段使用，正式环境从数据库加载）
BUILTIN_FAQ = [
    {
        "knowledge_id": "faq_001",
        "title": "退款时间",
        "content": "退款申请提交后，一般1-3个工作日内处理完成。如果是原路退回银行卡，可能需要3-7个工作日到账。",
        "type": "faq",
        "domain": "after_sales",
        "intent": ["refund_request"],
        "keywords": ["退款", "多久", "几天", "到账"],
    },
    {
        "knowledge_id": "faq_002",
        "title": "退货条件",
        "content": "普通商品签收后7天内，在不影响二次销售的情况下可申请退货退款。需保持商品完好、包装完整。虚拟商品一经发出不支持退货。",
        "type": "faq",
        "domain": "after_sales",
        "intent": ["return_request", "refund_request"],
        "keywords": ["退货", "条件", "7天", "退换"],
    },
    {
        "knowledge_id": "faq_003",
        "title": "物流延迟处理",
        "content": "如物流停滞超过48小时，您可以提交物流催促申请。如停滞超过72小时，可申请物流异常补偿。如超过7天未更新，可选择退款处理。",
        "type": "policy",
        "domain": "logistics",
        "intent": ["shipping_delay", "shipping_status"],
        "keywords": ["物流", "延迟", "没到", "停滞", "催促"],
    },
    {
        "knowledge_id": "faq_004",
        "title": "订单查询方式",
        "content": "您可以在'我的订单'页面查看所有订单状态。也可以提供订单号，我帮您查询具体的订单信息和物流状态。",
        "type": "faq",
        "domain": "general",
        "intent": ["order_status"],
        "keywords": ["订单", "查询", "查看", "状态"],
    },
    {
        "knowledge_id": "faq_005",
        "title": "退款规则",
        "content": "退款规则：1)未发货订单可全额退款；2)已发货未签收可申请拦截退款；3)已签收商品需满足退货条件后退款；4)单笔退款超过5000元需人工审核。",
        "type": "policy",
        "domain": "after_sales",
        "intent": ["refund_request"],
        "keywords": ["退款", "规则", "金额", "审核"],
        "forbidden_claims": ["不能承诺一定退款成功", "不能跳过质检流程"],
    },
    {
        "knowledge_id": "faq_006",
        "title": "人工客服服务时间",
        "content": "人工客服服务时间为每天9:00-22:00。非服务时间您可以留言，我们会在下个工作时间优先处理。",
        "type": "faq",
        "domain": "general",
        "intent": ["human_request"],
        "keywords": ["人工", "客服", "真人", "服务时间"],
    },
]


class KnowledgeService:
    """知识库服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self,
        query: str,
        intent: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        混合检索知识
        策略：FAQ精确匹配 + 关键词检索 + 向量检索
        """
        results = []

        # 1. FAQ精确匹配（从内置FAQ）
        faq_results = self._search_builtin_faq(query, intent)
        results.extend(faq_results)

        # 2. 数据库关键词检索
        db_results = await self._keyword_search(query, intent, top_k)
        results.extend(db_results)

        # 3. 合并去重并排序
        seen_ids = set()
        unique_results = []
        for item in results:
            kid = item.get("knowledge_id")
            if kid not in seen_ids:
                seen_ids.add(kid)
                unique_results.append(item)

        # 4. 过滤过期知识
        unique_results = self._filter_expired(unique_results)

        return unique_results[:top_k]

    def _search_builtin_faq(
        self, query: str, intent: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """从内置FAQ搜索"""
        results = []
        for faq in BUILTIN_FAQ:
            score = 0
            # 意图匹配
            if intent and intent in faq.get("intent", []):
                score += 0.5
            # 关键词匹配
            for keyword in faq.get("keywords", []):
                if keyword in query:
                    score += 0.3
            if score > 0.3:
                results.append({
                    **faq,
                    "score": score,
                    "source": "builtin_faq",
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    async def _keyword_search(
        self, query: str, intent: Optional[str], top_k: int
    ) -> List[Dict[str, Any]]:
        """数据库关键词检索"""
        try:
            stmt = select(KnowledgeChunk).where(
                KnowledgeChunk.status == "active"
            )
            if intent:
                stmt = stmt.where(
                    KnowledgeChunk.intent.contains([intent])
                )
            stmt = stmt.where(
                or_(
                    KnowledgeChunk.title.ilike(f"%{query}%"),
                    KnowledgeChunk.content.ilike(f"%{query}%"),
                )
            ).limit(top_k)

            result = await self.db.execute(stmt)
            chunks = result.scalars().all()

            return [
                {
                    "knowledge_id": c.knowledge_id,
                    "title": c.title,
                    "content": c.content,
                    "type": c.type,
                    "domain": c.domain,
                    "intent": c.intent,
                    "risk_level": c.risk_level,
                    "forbidden_claims": c.forbidden_claims,
                    "score": 0.6,
                    "source": "database",
                }
                for c in chunks
            ]
        except Exception as e:
            logger.error(f"数据库检索失败: {str(e)}")
            return []

    def _filter_expired(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤过期知识"""
        now = datetime.utcnow()
        filtered = []
        for item in results:
            expire_date = item.get("expire_date")
            if expire_date and isinstance(expire_date, datetime) and expire_date < now:
                continue
            filtered.append(item)
        return filtered

    # ===== 知识库管理方法 =====

    async def list_knowledge(
        self,
        page: int = 1,
        page_size: int = 20,
        type_filter: Optional[str] = None,
        domain_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> KnowledgeListResponse:
        """获取知识列表"""
        stmt = select(KnowledgeChunk)
        count_stmt = select(func.count(KnowledgeChunk.id))

        if type_filter:
            stmt = stmt.where(KnowledgeChunk.type == type_filter)
            count_stmt = count_stmt.where(KnowledgeChunk.type == type_filter)
        if domain_filter:
            stmt = stmt.where(KnowledgeChunk.domain == domain_filter)
            count_stmt = count_stmt.where(KnowledgeChunk.domain == domain_filter)
        if status_filter:
            stmt = stmt.where(KnowledgeChunk.status == status_filter)
            count_stmt = count_stmt.where(KnowledgeChunk.status == status_filter)
        if keyword:
            filter_cond = or_(
                KnowledgeChunk.title.ilike(f"%{keyword}%"),
                KnowledgeChunk.content.ilike(f"%{keyword}%"),
            )
            stmt = stmt.where(filter_cond)
            count_stmt = count_stmt.where(filter_cond)

        # 总数
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # 分页
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.order_by(KnowledgeChunk.updated_at.desc())

        result = await self.db.execute(stmt)
        items = result.scalars().all()

        return KnowledgeListResponse(
            total=total,
            items=items,
            page=page,
            page_size=page_size,
        )

    async def get_knowledge(self, knowledge_id: str) -> Optional[KnowledgeChunk]:
        """获取单条知识"""
        result = await self.db.execute(
            select(KnowledgeChunk).where(KnowledgeChunk.knowledge_id == knowledge_id)
        )
        return result.scalar_one_or_none()

    async def create_knowledge(self, data: KnowledgeCreate) -> KnowledgeChunk:
        """创建知识条目"""
        chunk = KnowledgeChunk(
            knowledge_id=data.knowledge_id,
            chunk_id=str(uuid.uuid4())[:8],
            title=data.title,
            content=data.content,
            type=data.type,
            domain=data.domain,
            intent=data.intent,
            product_category=data.product_category,
            user_type=data.user_type,
            region=data.region,
            version=data.version,
            effective_date=data.effective_date,
            expire_date=data.expire_date,
            risk_level=data.risk_level,
            owner=data.owner,
            need_human_review=data.need_human_review,
            source_doc=data.source_doc,
            forbidden_claims=data.forbidden_claims,
            status="draft",
        )
        self.db.add(chunk)
        await self.db.flush()
        await self.db.refresh(chunk)
        return chunk

    async def update_knowledge(
        self, knowledge_id: str, data: KnowledgeUpdate
    ) -> Optional[KnowledgeChunk]:
        """更新知识条目"""
        chunk = await self.get_knowledge(knowledge_id)
        if not chunk:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(chunk, key, value)
        chunk.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(chunk)
        return chunk

    async def publish_knowledge(self, knowledge_id: str):
        """发布知识"""
        chunk = await self.get_knowledge(knowledge_id)
        if chunk:
            chunk.status = "active"
            chunk.updated_at = datetime.utcnow()
            await self.db.flush()

    async def offline_knowledge(self, knowledge_id: str):
        """下线知识"""
        chunk = await self.get_knowledge(knowledge_id)
        if chunk:
            chunk.status = "offline"
            chunk.updated_at = datetime.utcnow()
            await self.db.flush()

    async def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计"""
        total = await self.db.execute(select(func.count(KnowledgeChunk.id)))
        active = await self.db.execute(
            select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.status == "active")
        )
        draft = await self.db.execute(
            select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.status == "draft")
        )

        return {
            "total": total.scalar() or 0,
            "active": active.scalar() or 0,
            "draft": draft.scalar() or 0,
            "builtin_faq_count": len(BUILTIN_FAQ),
        }
