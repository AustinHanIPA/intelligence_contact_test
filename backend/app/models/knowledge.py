"""
知识库模型
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Text, Integer, DateTime, Boolean, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.database import Base
from app.config import settings


class KnowledgeChunk(Base):
    """知识库切片表"""
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    knowledge_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    chunk_id: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(50), index=True)  # faq, policy, sop, product, tool_desc
    domain: Mapped[str] = mapped_column(String(50), index=True)  # after_sales, logistics, payment
    intent: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # 关联的意图列表
    product_category: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    user_type: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    region: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    version: Mapped[str] = mapped_column(String(20), default="v1.0")
    effective_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expire_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="low")  # low, medium, high
    owner: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    need_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    source_doc: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    forbidden_claims: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    embedding: Mapped[Optional[list]] = mapped_column(
        Vector(settings.EMBEDDING_DIMENSION), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, reviewing, active, offline
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_knowledge_type_domain", "type", "domain"),
        Index("idx_knowledge_status", "status"),
    )
