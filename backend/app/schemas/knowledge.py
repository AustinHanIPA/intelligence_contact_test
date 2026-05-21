"""
知识库相关Schema
"""
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class KnowledgeCreate(BaseModel):
    """创建知识条目"""
    knowledge_id: str
    title: str
    content: str
    type: str  # faq, policy, sop, product, tool_desc
    domain: str  # after_sales, logistics, payment, general
    intent: Optional[List[str]] = None
    product_category: Optional[List[str]] = None
    user_type: Optional[List[str]] = None
    region: Optional[List[str]] = None
    version: str = "v1.0"
    effective_date: Optional[datetime] = None
    expire_date: Optional[datetime] = None
    risk_level: str = "low"
    owner: Optional[str] = None
    need_human_review: bool = False
    source_doc: Optional[str] = None
    forbidden_claims: Optional[List[str]] = None


class KnowledgeUpdate(BaseModel):
    """更新知识条目"""
    title: Optional[str] = None
    content: Optional[str] = None
    type: Optional[str] = None
    domain: Optional[str] = None
    intent: Optional[List[str]] = None
    version: Optional[str] = None
    effective_date: Optional[datetime] = None
    expire_date: Optional[datetime] = None
    risk_level: Optional[str] = None
    owner: Optional[str] = None
    need_human_review: Optional[bool] = None
    forbidden_claims: Optional[List[str]] = None
    status: Optional[str] = None


class KnowledgeResponse(BaseModel):
    """知识条目响应"""
    id: int
    knowledge_id: str
    title: str
    content: str
    type: str
    domain: str
    intent: Optional[List[str]] = None
    version: str
    risk_level: str
    status: str
    hit_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeListResponse(BaseModel):
    """知识列表响应"""
    total: int
    items: List[KnowledgeResponse]
    page: int
    page_size: int
