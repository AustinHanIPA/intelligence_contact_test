"""
知识库管理API
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.knowledge import KnowledgeChunk
from app.schemas.knowledge import (
    KnowledgeCreate, KnowledgeUpdate, KnowledgeResponse, KnowledgeListResponse
)
from app.services.knowledge_service import KnowledgeService

router = APIRouter()


@router.get("/list", response_model=KnowledgeListResponse)
async def list_knowledge(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[str] = None,
    domain: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """获取知识库列表"""
    service = KnowledgeService(db)
    result = await service.list_knowledge(
        page=page,
        page_size=page_size,
        type_filter=type,
        domain_filter=domain,
        status_filter=status,
        keyword=keyword,
    )
    return result


@router.get("/{knowledge_id}", response_model=KnowledgeResponse)
async def get_knowledge(
    knowledge_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取单条知识详情"""
    service = KnowledgeService(db)
    knowledge = await service.get_knowledge(knowledge_id)
    if not knowledge:
        raise HTTPException(status_code=404, detail="知识条目不存在")
    return knowledge


@router.post("/create", response_model=KnowledgeResponse)
async def create_knowledge(
    data: KnowledgeCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建知识条目"""
    service = KnowledgeService(db)
    knowledge = await service.create_knowledge(data)
    return knowledge


@router.put("/{knowledge_id}", response_model=KnowledgeResponse)
async def update_knowledge(
    knowledge_id: str,
    data: KnowledgeUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新知识条目"""
    service = KnowledgeService(db)
    knowledge = await service.update_knowledge(knowledge_id, data)
    if not knowledge:
        raise HTTPException(status_code=404, detail="知识条目不存在")
    return knowledge


@router.post("/{knowledge_id}/publish")
async def publish_knowledge(
    knowledge_id: str,
    db: AsyncSession = Depends(get_db),
):
    """发布知识（审核通过后上线）"""
    service = KnowledgeService(db)
    await service.publish_knowledge(knowledge_id)
    return {"status": "ok", "message": "知识已发布"}


@router.post("/{knowledge_id}/offline")
async def offline_knowledge(
    knowledge_id: str,
    db: AsyncSession = Depends(get_db),
):
    """下线知识"""
    service = KnowledgeService(db)
    await service.offline_knowledge(knowledge_id)
    return {"status": "ok", "message": "知识已下线"}


@router.get("/stats/overview")
async def knowledge_stats(
    db: AsyncSession = Depends(get_db),
):
    """知识库统计概览"""
    service = KnowledgeService(db)
    stats = await service.get_stats()
    return stats
