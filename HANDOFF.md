# 智能客服系统 — 项目交接文档

> 更新日期：2026-05-21

---

## 1. 当前目标

基于 PRD 需求文档，构建一套端到端的智能客服系统，覆盖意图识别、知识库检索、规则引擎、工具调用、回复生成、人工转接等完整对话链路，并提供用户聊天界面和运营管理后台。

技术栈：Python FastAPI + React TypeScript + PostgreSQL (pgvector) + Redis

---

## 2. 已完成项

- 项目整体架构搭建（Docker Compose 编排）
- 数据库模型设计（KnowledgeChunk、CustomerSession、CandidateAction、ConversationLog、RuleLog、ToolCallLog、User）
- 13 步对话编排流水线（orchestrator）
- NLU 意图识别（14 种意图 + 情绪检测 + 实体提取，规则+LLM双轨策略）
- 知识库管理与检索（内置 FAQ + DB 存储 + 关键词匹配 + pgvector 向量检索 + 批量导入）
- 规则引擎（7 条规则：鉴权、高额退款、物流催促、补偿、情绪升级、重复投诉、虚拟商品）
- 候选动作生成与 Scorer 多维评分排序
- 工具调用模块（订单查询、物流追踪、退款/退货申请、工单创建、优惠券发放 — Mock 实现）
- 回复生成模块（模板 + LLM 可选）
- 人工转接与摘要生成
- 会话管理、反馈收集、分析统计
- 对话记忆管理（Redis 滑动窗口，10 轮上下文，2h TTL）
- JWT 认证服务（注册/登录/token 验证/角色权限）
- React 前端完整功能：
  - 登录/注册页面（带表单验证、错误提示）
  - 用户认证状态管理（authStore + localStorage 持久化）
  - 聊天界面（欢迎屏、快捷操作、消息气泡、动作按钮）
  - 运营后台（Dashboard、知识库管理、对话日志）
  - 受保护路由（未登录自动跳转 /login）
  - 401 响应自动登出 + 跳转
  - API 拦截器（请求自动附加 Bearer token，响应错误统一处理）
- Vite 代理配置（/api → localhost:8000）
- 单元测试全覆盖（56 项测试全部通过）：
  - NLU 意图/情绪/实体识别测试（23 项）
  - 规则引擎 7 条规则测试（16 项）
  - Scorer 评分排序测试（7 项）
  - 工具执行器测试（10 项）

---

## 3. 待办 / 后续优化

- [ ] 接入真实 OpenAI API（当前配置 OPENAI_API_KEY 即可开启，否则回退到规则/模板）
- [ ] 生产环境配置（Nginx 反代、HTTPS、日志收集）
- [ ] 性能压测与限流策略
- [ ] 知识库批量导入 UI（后端接口已实现，前端待对接）
- [ ] 前端管理后台完善（会话列表、知识库编辑弹窗）
- [ ] 集成测试（需实际 PostgreSQL + Redis 运行环境）

---

## 4. 关键文件索引

| 类别 | 路径 | 说明 |
|------|------|------|
| 入口 | `backend/app/main.py` | FastAPI 应用入口 |
| 核心编排 | `backend/app/services/orchestrator.py` | 13 步对话流水线 |
| NLU | `backend/app/services/nlu_service.py` | 意图/情绪/实体识别（规则+LLM） |
| 知识库 | `backend/app/services/knowledge_service.py` | 检索 + CRUD + 向量搜索 |
| 规则引擎 | `backend/app/services/rule_engine.py` | 7 条业务规则 |
| 评分决策 | `backend/app/services/scorer_service.py` | 多维加权评分 |
| 工具调用 | `backend/app/services/tool_executor.py` | Mock API |
| 认证服务 | `backend/app/services/auth_service.py` | JWT + bcrypt |
| LLM 服务 | `backend/app/services/llm_service.py` | OpenAI API 集成 |
| 向量服务 | `backend/app/services/embedding_service.py` | 文本向量化 |
| 对话记忆 | `backend/app/services/conversation_memory.py` | Redis 滑动窗口 |
| 数据模型 | `backend/app/models/` | SQLAlchemy ORM |
| API 路由 | `backend/app/api/` | chat / knowledge / session / admin / auth |
| 前端登录 | `frontend/src/pages/LoginPage.tsx` | 登录/注册界面 |
| 前端聊天 | `frontend/src/pages/ChatPage.tsx` | 用户对话界面 |
| 前端后台 | `frontend/src/pages/AdminPage.tsx` | 运营管理面板 |
| 认证状态 | `frontend/src/store/authStore.ts` | 用户 token 管理 |
| 聊天状态 | `frontend/src/store/chatStore.ts` | Zustand store |
| API 服务 | `frontend/src/services/api.ts` | Axios 封装+拦截器 |
| 基础设施 | `docker-compose.yml` | 一键编排 |
| DB 初始化 | `backend/init_db.py` | 建表 + 种子数据 |
| 测试 | `backend/tests/` | 56 项单元测试 |

---

## 5. 注意事项

1. **环境变量**：`backend/.env` 需配置 `DATABASE_URL`、`REDIS_URL`、`OPENAI_API_KEY`、`JWT_SECRET`，缺少时使用默认值。
2. **pgvector**：Docker 使用 `pgvector/pgvector:pg16` 镜像已内置扩展；本地开发需手动执行 `CREATE EXTENSION vector`。
3. **Mock 数据**：工具调用模块返回的是模拟数据，接入真实系统时替换 `tool_executor.py` 中的实现即可。
4. **端口**：前端 3000，后端 8000，PostgreSQL 5432，Redis 6379。
5. **Python 版本**：需 3.10+（兼容 3.9+ if/elif 写法）。
6. **首次启动**：务必先运行 `python3 init_db.py` 初始化数据库和种子数据。
7. **LLM 模式**：设置 `OPENAI_API_KEY` 后自动启用 LLM 增强（意图识别、回复生成），不设置则使用规则+模板兜底。

---

## 6. 快速启动

```bash
# Docker 一键启动
docker-compose up --build

# 访问
# 前端: http://localhost:3000
# 后端 API 文档: http://localhost:8000/docs

# 运行测试
cd backend
python -m pytest tests/ -v
```

---

## 7. 测试结果

```
56 passed in 0.40s
- test_nlu_service.py     : 23 tests (意图/情绪/实体/综合分析)
- test_rule_engine.py     : 16 tests (7条规则全覆盖)
- test_scorer_service.py  :  7 tests (打分/排序/场景权重)
- test_tool_executor.py   : 10 tests (工具调用/异常处理)
```
