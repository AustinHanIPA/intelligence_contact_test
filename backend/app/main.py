"""
智能客服系统 - 主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import router as api_router
from app.database import engine, Base

app = FastAPI(
    title="智能客服决策系统",
    description="基于知识库 + 工具调用 + 规则引擎 + 候选动作推荐的智能客服系统",
    version="1.0.0",
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """应用启动时初始化数据库表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.on_event("shutdown")
async def shutdown():
    """应用关闭时清理资源"""
    await engine.dispose()


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "intelligent-contact"}


# 注册路由
app.include_router(api_router, prefix="/api/v1")
