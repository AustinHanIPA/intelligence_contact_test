"""
知识库管理API
"""
import csv
import io
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
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


@router.post("/import")
async def import_knowledge(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    批量导入知识（支持CSV和JSON格式）
    CSV格式要求列：title, content, type, domain, intent(可选), risk_level(可选)
    JSON格式要求数组，每项包含 title, content 等字段
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="请上传文件")

    content = await file.read()
    items = []

    try:
        if file.filename.endswith(".csv"):
            # 解析CSV
            text_content = content.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text_content))
            for row in reader:
                item = {
                    "title": row.get("title", "").strip(),
                    "content": row.get("content", "").strip(),
                    "type": row.get("type", "faq").strip(),
                    "domain": row.get("domain", "general").strip(),
                    "risk_level": row.get("risk_level", "low").strip(),
                    "owner": row.get("owner", "").strip() or None,
                }
                # 解析intent（逗号分隔）
                intent_str = row.get("intent", "")
                if intent_str:
                    item["intent"] = [i.strip() for i in intent_str.split(",") if i.strip()]
                if item["title"] and item["content"]:
                    items.append(item)

        elif file.filename.endswith(".json"):
            # 解析JSON
            items = json.loads(content.decode("utf-8"))
            if not isinstance(items, list):
                raise HTTPException(status_code=400, detail="JSON文件应为数组格式")

        else:
            raise HTTPException(status_code=400, detail="仅支持 .csv 和 .json 格式文件")

    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {str(e)}")

    if not items:
        raise HTTPException(status_code=400, detail="未解析到有效数据")

    service = KnowledgeService(db)
    result = await service.batch_import(items)
    return result
