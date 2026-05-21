"""
NLU服务单元测试
"""
import pytest
from app.services.nlu_service import NLUService


@pytest.fixture
def nlu():
    return NLUService()


class TestIntentDetection:
    """意图识别测试"""

    def test_order_status_intent(self, nlu):
        intent, confidence = nlu._detect_intent("我想查一下订单")
        assert intent == "order_status"
        assert confidence > 0.3

    def test_shipping_status_intent(self, nlu):
        intent, confidence = nlu._detect_intent("我的快递到哪了")
        assert intent == "shipping_status"
        assert confidence > 0.3

    def test_shipping_delay_intent(self, nlu):
        intent, confidence = nlu._detect_intent("我的东西还没收到，好几天了")
        assert intent == "shipping_delay"
        assert confidence > 0.3

    def test_refund_request_intent(self, nlu):
        intent, confidence = nlu._detect_intent("我要退款")
        assert intent == "refund_request"
        assert confidence > 0.3

    def test_return_request_intent(self, nlu):
        intent, confidence = nlu._detect_intent("这个东西要退货")
        assert intent == "return_request"
        assert confidence > 0.3

    def test_human_request_intent(self, nlu):
        intent, confidence = nlu._detect_intent("转人工客服")
        assert intent == "human_request"
        assert confidence > 0.3

    def test_complaint_intent(self, nlu):
        intent, confidence = nlu._detect_intent("我要投诉，太差了")
        assert intent == "complaint"
        assert confidence > 0.3

    def test_unknown_intent(self, nlu):
        intent, confidence = nlu._detect_intent("今天天气怎么样")
        assert intent == "unknown"
        assert confidence <= 0.3

    def test_context_fallback_intent(self, nlu, mock_session):
        """当无法匹配时，从上下文继承"""
        mock_session.current_intent = "refund_request"
        intent, confidence = nlu._detect_intent("好的", mock_session)
        assert intent == "refund_request"
        assert confidence == 0.4


class TestEmotionDetection:
    """情绪识别测试"""

    def test_angry_emotion(self, nlu):
        assert nlu._detect_emotion("你们什么破东西，太离谱了") == "angry"

    def test_anxious_emotion(self, nlu):
        assert nlu._detect_emotion("能快点吗，我很着急") == "anxious"

    def test_disappointed_emotion(self, nlu):
        assert nlu._detect_emotion("太差了，非常失望") == "disappointed"

    def test_positive_emotion(self, nlu):
        assert nlu._detect_emotion("好的，谢谢") == "positive"

    def test_neutral_emotion(self, nlu):
        assert nlu._detect_emotion("我要查订单") == "neutral"


class TestEntityExtraction:
    """实体抽取测试"""

    def test_extract_order_id(self, nlu):
        entities = nlu._extract_entities("订单号：1234567890")
        assert entities.get("order_id") == "1234567890"

    def test_extract_order_id_from_number(self, nlu):
        entities = nlu._extract_entities("我的订单1234567890怎么还没到")
        assert entities.get("order_id") == "1234567890"

    def test_extract_amount(self, nlu):
        entities = nlu._extract_entities("退了199.5元还没到账")
        assert entities.get("amount") == 199.5

    def test_extract_amount_rmb(self, nlu):
        entities = nlu._extract_entities("我付了¥2999")
        assert entities.get("amount") == 2999.0

    def test_extract_time_ref(self, nlu):
        entities = nlu._extract_entities("3天前下的单")
        assert "3天前" in entities.get("time_ref", "")

    def test_no_entities(self, nlu):
        entities = nlu._extract_entities("帮我看看")
        assert entities == {}


class TestNLUAnalyze:
    """NLU综合分析测试"""

    @pytest.mark.asyncio
    async def test_analyze_refund_with_anger(self, nlu):
        result = await nlu.analyze("这什么破东西！我要退款！订单号123456789012")
        assert result["intent"] == "refund_request"
        assert result["emotion"] == "angry"
        assert "order_id" in result["entities"]
        assert result["confidence"] > 0.3

    @pytest.mark.asyncio
    async def test_analyze_shipping_query(self, nlu):
        result = await nlu.analyze("帮我查一下快递到哪了")
        assert result["intent"] == "shipping_status"
        assert result["emotion"] == "neutral"
        assert result["confidence"] > 0.3

    @pytest.mark.asyncio
    async def test_generate_clarification(self, nlu):
        result = await nlu.generate_clarification("嗯", "unknown")
        assert len(result) > 0
        assert "帮" in result or "服务" in result
