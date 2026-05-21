# FinAgent — 智能投研 Agent

基于 **LangGraph + RAG** 架构的 A 股投研助手，通过 LLM 驱动的多工具 Agent 分析股票行情、财务数据与研报。

---

## 技术栈

| 层次 | 技术 |
|------|------|
| Web 框架 | FastAPI + uvicorn，支持 SSE 流式输出 |
| LLM | DeepSeek（通过 langchain-openai 适配） |
| Agent 框架 | LangGraph（StateGraph + ToolNode） |
| Embedding | 硅基流动 BGE-M3 |
| 向量数据库 | Qdrant 1.12 |
| 关系数据库 | PostgreSQL 16（asyncpg + SQLAlchemy 2.0） |
| 缓存 / 会话 | Redis 7（AOF 持久化） |
| 数据源 | AKShare（免费）/ Tushare Pro（可选） |
| 包管理 | uv（pyproject.toml） |
| 日志 | loguru |

---

## 架构概览

```
用户请求
  │
  ▼
FastAPI (/chat, /chat/stream)
  │
  ▼
LangGraph Agent  ←──────────────────────────────────┐
  │  invoke / astream_events                         │
  ├─► agent_node (DeepSeek + tools)                  │
  │         │ tool_calls?                            │
  ├─► ToolNode                                       │
  │     ├─ lookup_ts_code      (中文名→ts_code)       │
  │     ├─ get_stock_info      (股票基本信息)          │
  │     ├─ get_stock_price     (历史行情)             │
  │     ├─ get_financial_report(财务指标)             │
  │     ├─ search_news         (个股新闻)             │
  │     └─ search_research_reports (Qdrant RAG)      │
  │               │                                  │
  │        数据源策略层 (DATA_SOURCE 配置)             │
  │         ├─ AKShareDataSource  (默认, 免费)         │
  │         └─ TushareDataSource  (需积分)            │
  │                                                  │
  └─► 对话历史写回 Redis ─────────────────────────────┘
```

**流式事件（SSE）类型：**
- `tool_call` — Agent 正在调用工具
- `tool_result` — 工具返回结果（截断至 500 字符）
- `token` — AI 输出文本片段
- `done` — 本轮完成

---

## 数据源设计

行情、财务、新闻三类数据通过**策略模式**解耦，一行配置即可切换数据源，工具层和 Agent 无感知。

```
工具层 (薄包装, 负责缓存 + LangChain tool 注册)
  └─► get_datasource()          ← 工厂单例, 读 DATA_SOURCE 环境变量
        ├─ AKShareDataSource    ← 腾讯/深交所/同花顺, 完全免费
        └─ TushareDataSource    ← Tushare Pro, 部分接口需 2000+ 积分
              ↑ 共同实现 StockDataSource ABC (5 个抽象方法)
```

| 功能 | AKShare（默认） | 数据来源 | Tushare |
|------|----------------|---------|---------|
| 名称→代码 | `stock_info_a_code_name` | AKShare | `stock_basic`（免费） |
| 股票基本信息 | `stock_info_sz_name_code` / `stock_info_sh_name_code` | 深交所 / 上交所官网 | `stock_basic`（免费） |
| 历史行情 | `stock_zh_a_hist_tx` | 腾讯财经 | `daily`（需 2000 积分） |
| 财务指标 | `stock_financial_abstract_ths` | 同花顺 | `fina_indicator`（需 2000 积分） |
| 个股新闻 | `stock_news_em` | 东方财富 | `news`（需积分） |

> **接口选型说明**：AKShare 模式下行情优先使用腾讯财经、基本信息使用交易所官网，避开对东方财富实时行情接口（`push2.eastmoney.com`）的依赖，在代理/VPN 环境下更稳定。

**扩展新数据源只需两步：**
1. 新建 `backend/app/datasource/xxx_source.py`，继承 `StockDataSource` 实现三个方法
2. 在 `factory.py` 的 `_REGISTRY` 中注册一行

---

## 项目结构

```
finagent/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI 应用入口（lifespan + CORS）
│   │   ├── api/
│   │   │   ├── health.py            # GET /health
│   │   │   ├── chat.py              # POST /chat, POST /chat/stream
│   │   │   └── ingest.py            # POST /ingest/report
│   │   ├── agents/
│   │   │   ├── research_agent.py    # LangGraph StateGraph, 含 invoke + stream
│   │   │   ├── session.py           # Redis 会话历史（load / save）
│   │   │   └── prompts.py           # 系统提示词（投研人格 + 合规边界）
│   │   ├── tools/                   # LangChain 工具层（薄包装）
│   │   │   ├── __init__.py          # ALL_TOOLS 列表
│   │   │   ├── lookup.py            # 中文股票名 → ts_code → datasource
│   │   │   ├── stock_info.py        # 股票基本信息
│   │   │   ├── stock_price.py       # 历史行情 → datasource
│   │   │   ├── financial_report.py  # 财务指标 → datasource
│   │   │   ├── news_search.py       # 个股新闻 → datasource
│   │   │   ├── rag_search.py        # 研报 RAG 检索
│   │   │   └── _aliases.py          # 股票常用别名（宁王/茅台等）
│   │   ├── datasource/              # 数据源策略层
│   │   │   ├── __init__.py          # 导出 get_datasource()
│   │   │   ├── base.py              # StockDataSource 抽象接口
│   │   │   ├── akshare_source.py    # AKShare 实现（默认）
│   │   │   ├── tushare_source.py    # Tushare 实现
│   │   │   └── factory.py           # 工厂单例，读 DATA_SOURCE 配置
│   │   ├── rag/
│   │   │   ├── embedder.py          # OpenAIEmbeddings (BGE-M3 endpoint)
│   │   │   ├── retriever.py         # Qdrant 向量检索
│   │   │   └── ingester.py          # PDF → chunks → Qdrant
│   │   ├── llm/
│   │   │   └── client.py            # get_llm() 单例
│   │   ├── core/
│   │   │   ├── config.py            # Settings (pydantic-settings)
│   │   │   ├── logger.py            # loguru 配置
│   │   │   ├── exceptions.py        # FinAgentError 层级
│   │   │   ├── cache.py             # Redis 工具缓存装饰器
│   │   │   └── redis_client.py      # Redis 异步客户端单例
│   │   └── models/
│   │       ├── chat.py              # ChatRequest, ChatResponse
│   │       ├── ingest.py            # IngestResponse
│   │       └── health.py            # HealthStatus
│   └── tests/
│       ├── conftest.py
│       └── test_health.py
├── docker/
│   └── postgres-init.sql
├── data/                            # 研报 PDF 存放目录
├── docker-compose.yml               # postgres + redis + qdrant
├── pyproject.toml
├── .env.example
└── .gitignore
```

---

## 快速启动

### 1. 克隆并安装依赖

```bash
git clone <repo-url>
cd finagent
uv sync
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，至少填入：
# - DEEPSEEK_API_KEY
# - TUSHARE_TOKEN（stock_basic 查询用，免费接口）
# DATA_SOURCE 默认 akshare，行情/财务/新闻无需额外积分
```

### 3. 启动基础设施

```bash
docker compose up -d
# 等待 postgres / redis / qdrant 健康检查通过
```

### 4. 启动后端

```bash
uv run uvicorn backend.app.main:app --reload
```

服务启动后访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

---

## API 说明

### POST /chat

一次性对话，返回完整答案与工具调用记录。

```json
// 请求
{
  "message": "帮我分析一下宁德时代最近的财务状况",
  "session_id": "可选，不传则自动生成"
}

// 响应
{
  "session_id": "xxx",
  "answer": "...",
  "tool_calls": [
    {"name": "lookup_ts_code", "args": {"name": "宁德时代"}},
    {"name": "get_financial_report", "args": {"ts_code": "300750.SZ", "period": "20241231"}}
  ]
}
```

### POST /chat/stream

SSE 流式对话，实时推送工具调用过程和 AI 输出片段。

```powershell
# PowerShell
$body = '{"message": "分析比亚迪的股价走势"}'
Invoke-RestMethod -Method POST -Uri http://localhost:8000/chat -ContentType "application/json" -Body $body
```

### POST /ingest/report

上传研报 PDF，写入 Qdrant 向量数据库。

---

## 配置项（.env）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATA_SOURCE` | `akshare` | 行情数据源：`akshare`（免费）\| `tushare`（需积分） |
| `DEEPSEEK_API_KEY` | — | DeepSeek API Key |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` | |
| `LLM_MODEL` | `deepseek-chat` | |
| `EMBEDDING_API_KEY` | — | 硅基流动 API Key（免费额度 2000 万 tokens） |
| `EMBEDDING_BASE_URL` | `https://api.siliconflow.cn/v1` | |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | |
| `TUSHARE_TOKEN` | — | Tushare Pro Token（stock_basic 免费，其余接口需积分） |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL 连接串 |
| `REDIS_URL` | `redis://localhost:6379/0` | |
| `QDRANT_URL` | `http://localhost:6333` | |
| `SESSION_TTL` | `3600` | 会话历史保留时长（秒） |
| `SESSION_MAX_MESSAGES` | `20` | 单会话最多保留消息条数 |

---

## 开发进度

- [x] Day 1 — FastAPI 脚手架：配置、日志、健康检查、Docker 基础设施
- [x] Day 1.5 — 补全项目结构：models / llm / agents / tools / rag / tests
- [x] Day 2 — 接入 DeepSeek LLM，`/chat` 路由可用
- [x] Day 3 — LangGraph Agent：多工具调用 + Redis 会话历史 + SSE 流式输出
- [x] Day 3.5 — 数据源策略层：AKShare / Tushare 可配置切换；AKShare 接口适配（腾讯财经行情、交易所官网基本信息、同花顺财务）
- [ ] Day 4 — 完整 RAG 导入（`rag/ingester.py` PDF 解析与写入）
- [ ] Frontend — 前端界面（未开始）

---

## 开发工具

```bash
# 代码检查
uv run ruff check .

# 运行测试
uv run pytest

# 格式化
uv run ruff format .
```
