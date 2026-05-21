"""
工具执行器单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.tool_executor import ToolExecutor


@pytest.fixture
def executor(mock_db):
    return ToolExecutor(mock_db)


class TestToolExecutor:
    @pytest.mark.asyncio
    async def test_order_query_success(self, executor):
        result = await executor.execute(
            tool_name="order_query",
            params={"order_id": "123456"},
            session_id="test-session",
        )
        assert result["success"] is True
        assert result["data"]["order_id"] == "123456"
        assert result["data"]["product"] == "Nintendo Switch"

    @pytest.mark.asyncio
    async def test_logistics_query_success(self, executor):
        result = await executor.execute(
            tool_name="logistics_query",
            params={"order_id": "123456"},
            session_id="test-session",
        )
        assert result["success"] is True
        assert result["data"]["carrier"] == "顺丰快递"
        assert result["data"]["stagnant_hours"] == 52

    @pytest.mark.asyncio
    async def test_refund_check_eligible(self, executor):
        result = await executor.execute(
            tool_name="refund_check",
            params={"order_id": "123456"},
            session_id="test-session",
        )
        assert result["success"] is True
        assert result["data"]["eligible"] is True
        assert result["data"]["refund_amount"] == 2199.00

    @pytest.mark.asyncio
    async def test_logistics_urge_default(self, executor):
        result = await executor.execute(
            tool_name="logistics_urge",
            params={"order_id": "123456"},
            session_id="test-session",
        )
        assert result["success"] is True
        assert "urge_id" in result["data"]

    @pytest.mark.asyncio
    async def test_refund_submit_default(self, executor):
        result = await executor.execute(
            tool_name="refund_submit",
            params={"order_id": "123456", "reason": "不想要了"},
            session_id="test-session",
        )
        assert result["success"] is True
        assert "refund_id" in result["data"]

    @pytest.mark.asyncio
    async def test_ticket_create_default(self, executor):
        result = await executor.execute(
            tool_name="ticket_create",
            params={"order_id": "123456", "user_id": "user_001"},
            session_id="test-session",
        )
        assert result["success"] is True
        assert "ticket_id" in result["data"]

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_not_found(self, executor):
        result = await executor.execute(
            tool_name="unknown_tool",
            params={},
            session_id="test-session",
        )
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_nonexistent_order_returns_not_found(self, executor):
        result = await executor.execute(
            tool_name="order_query",
            params={"order_id": "999999"},
            session_id="test-session",
        )
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_coupon_issue(self, executor):
        result = await executor.execute(
            tool_name="coupon_issue",
            params={},
            session_id="test-session",
        )
        assert result["success"] is True
        assert result["data"]["amount"] == 10.00

    @pytest.mark.asyncio
    async def test_return_check(self, executor):
        result = await executor.execute(
            tool_name="return_check",
            params={"order_id": "789012"},
            session_id="test-session",
        )
        assert result["success"] is True
        assert result["data"]["eligible"] is True
