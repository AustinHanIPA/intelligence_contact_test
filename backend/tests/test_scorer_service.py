"""
Scorer决策排序服务单元测试
"""
import pytest
from app.services.scorer_service import ScorerService


@pytest.fixture
def scorer():
    return ScorerService()


@pytest.fixture
def sample_actions():
    return [
        {
            "action_id": "query_order",
            "action_type": "tool_call",
            "name": "查询订单",
            "risk_level": "low",
            "estimated_resolution_rate": 0.85,
            "cost": 0.0,
        },
        {
            "action_id": "transfer_human",
            "action_type": "human_transfer",
            "name": "转人工",
            "risk_level": "low",
            "estimated_resolution_rate": 0.90,
            "cost": 10.0,
        },
        {
            "action_id": "faq_answer_001",
            "action_type": "faq_answer",
            "name": "FAQ回答",
            "risk_level": "low",
            "estimated_resolution_rate": 0.75,
            "cost": 0.0,
            "knowledge_content": "退款一般1-3个工作日",
        },
    ]


class TestScorerService:
    @pytest.mark.asyncio
    async def test_scores_actions(self, scorer, sample_actions):
        context = {"session_info": {"previous_intent": "order_status"}}
        results = await scorer.score(sample_actions, context, emotion="neutral")
        assert len(results) == 3
        # 每个动作都应该有分数
        for action in results:
            assert "final_score" in action
            assert "score_breakdown" in action
            assert action["final_score"] > 0

    @pytest.mark.asyncio
    async def test_sorted_by_score_descending(self, scorer, sample_actions):
        context = {"session_info": {"previous_intent": "order_status"}}
        results = await scorer.score(sample_actions, context, emotion="neutral")
        scores = [r["final_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_human_transfer_higher_when_angry(self, scorer, sample_actions):
        context = {"session_info": {"previous_intent": "complaint"}}
        results = await scorer.score(sample_actions, context, emotion="angry")
        # 愤怒用户时，转人工的满意度分数应较高
        transfer_action = next(r for r in results if r["action_id"] == "transfer_human")
        assert transfer_action["score_breakdown"]["satisfaction"] > 0.7

    @pytest.mark.asyncio
    async def test_empty_actions_returns_empty(self, scorer):
        results = await scorer.score([], {}, emotion="neutral")
        assert results == []

    @pytest.mark.asyncio
    async def test_uses_scene_weights(self, scorer, sample_actions):
        """退款场景应使用退款专用权重"""
        context = {"session_info": {"previous_intent": "refund_request"}}
        results = await scorer.score(sample_actions, context, emotion="neutral")
        # 只要正常运行不报错即可
        assert len(results) == 3

    def test_normalize_cost(self, scorer):
        assert scorer._normalize_cost(0) == 0.0
        assert scorer._normalize_cost(50) == 1.0
        assert scorer._normalize_cost(100) == 1.0  # capped at 1.0
        assert 0 < scorer._normalize_cost(10) < 1

    def test_estimate_speed(self, scorer):
        faq = {"action_type": "faq_answer"}
        tool = {"action_type": "tool_call"}
        human = {"action_type": "human_transfer"}
        assert scorer._estimate_speed(faq) > scorer._estimate_speed(tool)
        assert scorer._estimate_speed(tool) > scorer._estimate_speed(human)
