"""
API路由注册
"""
from fastapi import APIRouter

from app.api.chat import router as chat_router
from app.api.knowledge import router as knowledge_router
from app.api.session import router as session_router
from app.api.admin import router as admin_router

router = APIRouter()

router.include_router(chat_router, prefix="/chat", tags=["聊天"])
router.include_router(knowledge_router, prefix="/knowledge", tags=["知识库"])
router.include_router(session_router, prefix="/sessions", tags=["会话管理"])
router.include_router(admin_router, prefix="/admin", tags=["管理后台"])
