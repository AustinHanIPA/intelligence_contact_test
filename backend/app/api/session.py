"""
会话管理API
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.session import SessionResponse, HandoffRequest, HandoffSummary
from app.services.session_manager import SessionManager
from app.services.handoff_service import HandoffService

router = APIRouter()


@router.get("/list", response_model=List[SessionResponse])
async def list_sessions(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取会话列表"""
    manager = SessionManager(db)
    sessions = await manager.list_sessions(
        user_id=user_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    return sessions


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取会话详情"""
    manager = SessionManager(db)
    session = await manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session


@router.post("/handoff", response_model=HandoffSummary)
async def handoff_to_human(
    request: HandoffRequest,
    db: AsyncSession = Depends(get_db),
):
    """转接人工客服"""
    service = HandoffService(db)
    summary = await service.create_handoff(
        session_id=request.session_id,
        reason=request.reason,
    )
    return summary


@router.get("/{session_id}/history")
async def get_session_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取会话对话历史"""
    manager = SessionManager(db)
    history = await manager.get_conversation_history(session_id)
    return {"session_id": session_id, "messages": history}


@router.post("/{session_id}/close")
async def close_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """关闭会话"""
    manager = SessionManager(db)
    await manager.close_session(session_id)
    return {"status": "ok", "message": "会话已关闭"}
