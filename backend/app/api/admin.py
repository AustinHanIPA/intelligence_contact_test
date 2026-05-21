"""
管理后台API
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
):
    """获取仪表板数据"""
    from app.services.analytics_service import AnalyticsService
    service = AnalyticsService(db)
    return await service.get_dashboard_data()


@router.get("/logs/conversations")
async def get_conversation_logs(
    session_id: Optional[str] = None,
    intent: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取对话日志"""
    from app.services.analytics_service import AnalyticsService
    service = AnalyticsService(db)
    return await service.get_conversation_logs(
        session_id=session_id,
        intent=intent,
        page=page,
        page_size=page_size,
    )


@router.get("/logs/rules")
async def get_rule_logs(
    session_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取规则命中日志"""
    from app.services.analytics_service import AnalyticsService
    service = AnalyticsService(db)
    return await service.get_rule_logs(
        session_id=session_id,
        page=page,
        page_size=page_size,
    )


@router.get("/logs/tools")
async def get_tool_logs(
    session_id: Optional[str] = None,
    tool_name: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取工具调用日志"""
    from app.services.analytics_service import AnalyticsService
    service = AnalyticsService(db)
    return await service.get_tool_logs(
        session_id=session_id,
        tool_name=tool_name,
        page=page,
        page_size=page_size,
    )


@router.get("/metrics")
async def get_metrics(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """获取关键指标"""
    from app.services.analytics_service import AnalyticsService
    service = AnalyticsService(db)
    return await service.get_metrics(days=days)
