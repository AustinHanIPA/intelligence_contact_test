"""
规则引擎单元测试
"""
import pytest
from unittest.mock import MagicMock
from app.services.rule_engine import (
    AuthVerificationRule,
    RefundAmountRule,
    LogisticsUrgeRule,
    CompensationRule,
    EmotionEscalationRule,
    ComplaintCountRule,
    VirtualProductRule,
)


@pytest.fixture
def session():
    s = MagicMock()
    s.session_id = "test-session"
    s.emotion = "neutral"
    s.message_count = 1
    return s


class TestAuthVerificationRule:
    def test_blocks_unverified_user_sensitive_action(self, session):
        rule = AuthVerificationRule()
        context = {"user_info": {"verified": False}}
        action = {"action_id": "query_order"}
        result = rule.evaluate(action, context, session)
        assert result["passed"] is False
        assert "未验证" in result["reason"]

    def test_allows_verified_user(self, session):
        rule = AuthVerificationRule()
        context = {"user_info": {"verified": True}}
        action = {"action_id": "query_order"}
        result = rule.evaluate(action, context, session)
        assert result["passed"] is True

    def test_allows_non_sensitive_action_for_unverified(self, session):
        rule = AuthVerificationRule()
        context = {"user_info": {"verified": False}}
        action = {"action_id": "ask_clarification"}
        result = rule.evaluate(action, context, session)
        assert result["passed"] is True


class TestRefundAmountRule:
    def test_blocks_high_amount_refund(self, session):
        rule = RefundAmountRule()
        context = {"order_info": {"amount": 6000}}
        action = {"action_id": "submit_refund"}
        result = rule.evaluate(action, context, session)
        assert result["passed"] is False
        assert "5000" in result["reason"]
        assert result.get("force_handoff") is True

    def test_allows_normal_amount_refund(self, session):
        rule = RefundAmountRule()
        context = {"order_info": {"amount": 200}}
        action = {"action_id": "submit_refund"}
        result = rule.evaluate(action, context, session)
        assert result["passed"] is True

    def test_ignores_non_refund_actions(self, session):
        rule = RefundAmountRule()
        context = {"order_info": {"amount": 10000}}
        action = {"action_id": "query_order"}
        result = rule.evaluate(action, context, session)
        assert result["passed"] is True


class TestLogisticsUrgeRule:
    def test_blocks_early_urge(self, session):
        rule = LogisticsUrgeRule()
        context = {"logistics_info": {"stagnant_hours": 24}}
        action = {"action_id": "urge_logistics"}
        result = rule.evaluate(action, context, session)
        assert result["passed"] is False
        assert "48" in result["reason"]

    def test_allows_urge_after_48h(self, session):
        rule = LogisticsUrgeRule()
        context = {"logistics_info": {"stagnant_hours": 50}}
        action = {"action_id": "urge_logistics"}
        result = rule.evaluate(action, context, session)
        assert result["passed"] is True


class TestCompensationRule:
    def test_blocks_early_compensation(self, session):
        rule = CompensationRule()
        context = {"logistics_info": {"stagnant_hours": 60}}
        action = {"action_id": "offer_compensation"}
        result = rule.evaluate(action, context, session)
        assert result["passed"] is False

    def test_allows_compensation_after_72h(self, session):
        rule = CompensationRule()
        context = {"logistics_info": {"stagnant_hours": 80}}
        action = {"action_id": "offer_compensation"}
        result = rule.evaluate(action, context, session)
        assert result["passed"] is True


class TestEmotionEscalationRule:
    def test_suggests_handoff_for_angry_multi_turn(self, session):
        rule = EmotionEscalationRule()
        session.emotion = "angry"
        session.message_count = 4
        result = rule.evaluate({}, {}, session)
        assert result["passed"] is True
        assert result.get("suggest_handoff") is True

    def test_no_handoff_for_calm_user(self, session):
        rule = EmotionEscalationRule()
        session.emotion = "neutral"
        session.message_count = 5
        result = rule.evaluate({}, {}, session)
        assert result.get("suggest_handoff") is None


class TestComplaintCountRule:
    def test_force_handoff_for_repeated_complaints(self, session):
        rule = ComplaintCountRule()
        context = {"risk_info": {"complaint_count": 3}}
        result = rule.evaluate({}, context, session)
        assert result.get("force_handoff") is True

    def test_no_handoff_for_first_time(self, session):
        rule = ComplaintCountRule()
        context = {"risk_info": {"complaint_count": 1}}
        result = rule.evaluate({}, context, session)
        assert result.get("force_handoff") is None


class TestVirtualProductRule:
    def test_blocks_virtual_product_return(self, session):
        rule = VirtualProductRule()
        context = {"order_info": {"product_category": "virtual"}}
        action = {"action_id": "submit_return"}
        result = rule.evaluate(action, context, session)
        assert result["passed"] is False

    def test_allows_physical_product_return(self, session):
        rule = VirtualProductRule()
        context = {"order_info": {"product_category": "electronics"}}
        action = {"action_id": "submit_return"}
        result = rule.evaluate(action, context, session)
        assert result["passed"] is True
