"""
测试配置和通用 fixtures
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db():
    """模拟数据库会话"""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def mock_session():
    """模拟用户会话"""
    session = MagicMock()
    session.session_id = "test-session-001"
    session.user_id = "user_001"
    session.current_intent = None
    session.emotion = None
    session.slots = {}
    session.message_count = 1
    session.verified = True
    session.status = "active"
    session.context = None
    return session
