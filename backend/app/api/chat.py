"""
聊天API - 核心对话接口
"""
import uuid
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse, FeedbackRequest, ActionButton, MessageType
from app.services.orchestrator import ConversationOrchestrator
from app.services.session_manager import SessionManager

router = APIRouter()


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    用户发送消息 - 核心对话接口
    处理流程：意图识别 → 上下文补全 → 知识检索 → 候选生成 → 规则过滤 → 打分排序 → 回复生成
    """
    start_time = time.time()

    # 获取或创建会话
    session_manager = SessionManager(db)
    session = await session_manager.get_or_create_session(
        session_id=request.session_id,
        user_id=request.user_id,
    )

    # 核心对话编排
    orchestrator = ConversationOrchestrator(db)
    response = await orchestrator.process_message(
        session=session,
        user_message=request.message,
        metadata=request.metadata,
    )

    # 记录响应时间
    response_time = int((time.time() - start_time) * 1000)

    return response


@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """用户提交反馈"""
    from app.services.feedback_service import FeedbackService
    service = FeedbackService(db)
    await service.record_feedback(
        session_id=request.session_id,
        log_id=request.log_id,
        feedback=request.feedback,
        comment=request.comment,
    )
    return {"status": "ok", "message": "反馈已记录"}


@router.post("/action")
async def execute_action(
    session_id: str,
    action_id: str,
    params: dict = None,
    db: AsyncSession = Depends(get_db),
):
    """执行用户选择的动作（按钮点击等）"""
    orchestrator = ConversationOrchestrator(db)
    response = await orchestrator.execute_action(
        session_id=session_id,
        action_id=action_id,
        params=params or {},
    )
    return response
