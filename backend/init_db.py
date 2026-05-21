"""
数据库初始化脚本
创建表结构并插入初始测试数据
"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.database import engine, Base, async_session
from app.models import *
from app.models.user import User
from app.models.knowledge import KnowledgeChunk
from app.models.action import CandidateAction


async def init_database():
    """初始化数据库"""
    print("正在创建数据库表...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("数据库表创建完成！")

    # 插入测试数据
    async with async_session() as session:
        # 检查是否已有数据
        from sqlalchemy import select, func
        result = await session.execute(select(func.count(User.id)))
        if result.scalar() > 0:
            print("数据库已有数据，跳过初始化。")
            return

        print("正在插入测试数据...")

        # 创建测试用户
        users = [
            User(user_id="user_001", username="张三", email="zhangsan@test.com",
                 role="customer", member_level="vip"),
            User(user_id="user_002", username="李四", email="lisi@test.com",
                 role="customer", member_level="normal"),
            User(user_id="agent_001", username="客服小王", email="wang@company.com",
                 role="agent", member_level="normal"),
            User(user_id="admin_001", username="管理员", email="admin@company.com",
                 role="admin", member_level="normal"),
        ]
        session.add_all(users)

        # 创建知识库数据
        knowledge_items = [
            KnowledgeChunk(
                knowledge_id="kb_policy_001",
                chunk_id="chunk_001",
                title="7天无理由退货政策",
                content="普通商品签收后7天内，在不影响二次销售的情况下可申请退货退款。需保持商品完好、包装完整、配件齐全。虚拟商品和定制商品不适用此政策。",
                type="policy",
                domain="after_sales",
                intent=["return_request", "refund_request"],
                version="v1.0",
                risk_level="low",
                owner="after_sales_team",
                status="active",
                forbidden_claims=["不能承诺一定退款成功", "不能跳过质检流程"],
            ),
            KnowledgeChunk(
                knowledge_id="kb_policy_002",
                chunk_id="chunk_002",
                title="物流延迟补偿规则",
                content="物流停滞超过48小时可提交催促申请；停滞超过72小时可申请5-10元无门槛补偿券；停滞超过7天可申请全额退款。",
                type="policy",
                domain="logistics",
                intent=["shipping_delay"],
                version="v1.0",
                risk_level="medium",
                owner="logistics_team",
                status="active",
            ),
            KnowledgeChunk(
                knowledge_id="kb_faq_001",
                chunk_id="chunk_003",
                title="退款到账时间",
                content="退款审核通过后，原路退回银行卡一般需要3-7个工作日到账；退回余额一般即时到账；退回第三方支付一般1-3个工作日到账。",
                type="faq",
                domain="after_sales",
                intent=["refund_request"],
                version="v1.0",
                risk_level="low",
                owner="after_sales_team",
                status="active",
            ),
        ]
        session.add_all(knowledge_items)

        await session.commit()
        print("测试数据插入完成！")

    print("\n数据库初始化完成！")
    print("可以使用以下命令启动后端服务：")
    print("  cd backend && python run.py")


if __name__ == "__main__":
    asyncio.run(init_database())
