# AI-Infra 运行文档

本文档是 AI-Infra 的**完整运行手册**，涵盖环境准备、Docker 部署、本地开发、BGE 模型、控制台、SDK、K8s 与排障。

架构与设计说明见 [README.md](README.md)。

---

## 目录

1. [环境要求](#1-环境要求)
2. [初次配置](#2-初次配置)
3. [Docker Compose 一键部署（推荐）](#3-docker-compose-一键部署推荐)
4. [本地开发模式](#4-本地开发模式)
5. [Gateway 使用](#5-gateway-使用)
   - [5.5 智能模型路由](#55-智能模型路由)
   - [5.6 自托管推理（Inference + vLLM）](#56-自托管推理inference--vllm)
   - [5.7 Agent 运行时](#57-agent-运行时)
6. [RAG 知识库使用](#6-rag-知识库使用)
7. [本地 BGE 模型](#7-本地-bge-模型)
8. [Web 管理控制台](#8-web-管理控制台)
9. [Python SDK](#9-python-sdk)
10. [Kubernetes 部署](#10-kubernetes-部署)
11. [监控（Prometheus + Grafana）](#11-监控prometheus--grafana)
12. [环境变量参考](#12-环境变量参考)
13. [API 速查](#13-api-速查)
14. [常见问题](#14-常见问题)

---

## 1. 环境要求

### 最低要求（Docker 模式）

| 工具 | 版本建议 |
|------|----------|
| Docker | 24+ |
| Docker Compose | v2+ |
| 磁盘 | ≥ 20 GB（含 Milvus；使用 BGE 建议 ≥ 30 GB） |
| 内存 | ≥ 8 GB（RAG + Milvus + BGE 建议 ≥ 16 GB） |

### 本地开发额外要求

| 工具 | 版本建议 |
|------|----------|
| Python | 3.10+ |
| Node.js | 18+（控制台开发） |
| MySQL | 8.0 |
| Redis | 7 |

### K8s 部署额外要求

| 工具 | 说明 |
|------|------|
| Kubernetes | minikube / kind / 云集群 |
| kubectl | 已配置集群上下文 |
| docker | 构建镜像 |

---

## 2. 初次配置

### 2.1 克隆项目

```bash
git clone <your-repo-url> AI-Infra
cd AI-Infra
```

### 2.2 创建配置文件

```powershell
# Windows
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

### 2.3 必填项

编辑项目根目录 `.env`，至少配置：

```env
MODEL_API_KEY=sk-your-real-api-key
MODEL_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o-mini

ADMIN_TOKEN=your-strong-admin-token
```

> **说明**
> - `MODEL_*`：Gateway 代理对话、RAG 问答、API Embedding 时使用
> - `ADMIN_TOKEN`：管理 API（创建 Key、知识库操作）及 Web 控制台鉴权
> - 配置统一放在**项目根目录** `.env`，由 `common/config.py` 加载

### 2.4 创建运行时目录

```powershell
# Windows
New-Item -ItemType Directory -Force -Path logs, data, models

# Linux / macOS
mkdir -p logs data models
```

---

## 3. Docker Compose 一键部署（推荐）

### 3.1 启动全部服务

```powershell
# Windows
.\scripts\start.ps1

# Linux / macOS
./scripts/start.sh
```

首次运行会自动从 `.env.example` 复制 `.env`（若不存在）。

### 3.2 启动的服务

| 容器 | 说明 |
|------|------|
| mysql | 元数据（API Key、知识库、文档） |
| redis | Gateway 限流 |
| etcd + minio + milvus | 向量库依赖 |
| gateway | 模型网关 :8080 |
| inference | 自托管推理代理 :8082（转发至 vLLM） |
| agent | Agent 运行时 :8083 |
| rag | RAG 服务 :8081 |
| console | Web 管理台 :3000 |

### 3.3 验证

```bash
# Gateway
curl http://localhost:8080/health

# RAG
curl http://localhost:8081/health

# Inference（需 vLLM 就绪后 /ready 才通过）
curl http://localhost:8082/health

# Agent
curl http://localhost:8083/health

# Console
curl -I http://localhost:3000
```

预期 RAG health 示例：

```json
{
  "status": "ok",
  "service": "rag",
  "embedding_backend": "api",
  "rerank_backend": "off",
  "embedding_dimension": 1536
}
```

> Milvus 首次启动约需 1–2 分钟，RAG `/ready` 在 Milvus 就绪前可能失败，稍等重试。

### 3.4 停止与清理

```bash
cd deploy/docker-compose
docker compose down          # 停止
docker compose down -v       # 停止并删除数据卷（⚠️ 清空数据库与向量）
```

### 3.5 服务访问地址

| 服务 | 地址 |
|------|------|
| Gateway API | http://localhost:8080 |
| Gateway Swagger | http://localhost:8080/docs |
| Inference API | http://localhost:8082 |
| Inference Swagger | http://localhost:8082/docs |
| Agent API | http://localhost:8083 |
| Agent Swagger | http://localhost:8083/docs |
| RAG API | http://localhost:8081 |
| RAG Swagger | http://localhost:8081/docs |
| Web 控制台 | http://localhost:3000 |
| MinIO Console | http://localhost:9001 |
| 运行日志 | `logs/app.log` |

---

## 4. 本地开发模式

本地开发时不使用 Docker 跑应用，但基础设施（MySQL、Redis、Milvus 等）仍可用 Docker Compose 只启动部分服务。

### 4.1 仅启动基础设施

```bash
cd deploy/docker-compose
docker compose up -d mysql redis etcd minio milvus
```

`.env` 中保持 `MYSQL_HOST=localhost` 等本地地址。

### 4.2 启动 Gateway

```bash
pip install -r services/gateway/requirements.txt
python scripts/run_gateway.py
```

访问：http://localhost:8080/docs

### 4.3 启动 RAG

```bash
pip install -r services/rag/requirements.txt

# 若使用本地 BGE（见第 7 节）
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r services/rag/requirements-bge.txt

python scripts/run_rag.py
```

访问：http://localhost:8081/docs

### 4.5 启动 Inference

```bash
pip install -r services/inference/requirements.txt
python scripts/run_inference.py
```

访问：http://localhost:8082/docs

> Inference 本身不加载模型，需单独启动 vLLM（见 [5.6 节](#56-自托管推理inference--vllm)）。

### 4.6 启动 Agent

```bash
pip install -r services/agent/requirements.txt
python scripts/run_agent.py
```

访问：http://localhost:8083/docs

> Agent 依赖 RAG 与 LLM（`MODEL_API_KEY`），本地开发时 `.env` 中 `RAG_INTERNAL_URL=http://localhost:8081`。

### 4.7 启动控制台（前端热更新）

```powershell
# 需 gateway + rag 已运行
.\scripts\run_console.ps1
# 或 ./scripts/run_console.sh
```

访问：http://localhost:5173（Vite 开发服务器，自动代理 `/api/gateway` 和 `/api/rag`）

### 4.8 PYTHONPATH 说明

`run_gateway.py` / `run_rag.py` / `run_inference.py` / `run_agent.py` 已自动设置：

```
PYTHONPATH = 项目根目录 + services/gateway（或 services/rag）
```

手动运行测试时需：

```bash
export PYTHONPATH=/path/to/AI-Infra:/path/to/AI-Infra/services/gateway
```

---

## 5. Gateway 使用

### 5.1 创建 API Key

```bash
curl -X POST http://localhost:8080/admin/keys \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "demo-app", "tenant_id": "team-a"}'
```

响应中 `api_key` 字段**仅显示一次**，请立即保存。

### 5.2 对话补全（OpenAI 兼容）

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer sk-aiinfra-xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### 5.3 流式输出

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer sk-aiinfra-xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": true
  }'
```

### 5.4 Gateway API 列表

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/health` | 无 | 健康检查 |
| GET | `/ready` | 无 | MySQL + Redis 就绪 |
| GET | `/metrics` | 无 | Prometheus 指标 |
| POST | `/v1/chat/completions` | API Key | 对话补全 |
| GET | `/admin/models` | Admin Token | 模型列表 |
| GET | `/admin/keys` | Admin Token | Key 列表 |
| POST | `/admin/keys` | Admin Token | 创建 Key |

### 5.5 智能模型路由

Gateway 内置 `common/model_router.py`，支持三种路由能力：

| 能力 | 配置 / 用法 | 说明 |
|------|-------------|------|
| **智能选模** | 请求 `"model": "auto"` | 按消息估算 token 数，低于阈值走小模型，高于阈值走大模型 |
| **本地/API 分流** | `LOCAL_MODELS` | 列表中的模型名走 Inference → vLLM，其余走 `MODEL_BASE_URL` |
| **Fallback** | `FALLBACK_MODEL` | 上游 5xx 或超时自动切换备用模型 |

**.env 关键配置：**

```env
ROUTING_ENABLED=true
ROUTING_TOKEN_THRESHOLD=2000
ROUTING_SIMPLE_MODEL=gpt-4o-mini
ROUTING_COMPLEX_MODEL=gpt-4o
FALLBACK_MODEL=gpt-4o-mini
LOCAL_MODELS=qwen2.5-7b-instruct
AVAILABLE_MODELS=auto,gpt-4o-mini,gpt-4o,qwen2.5-7b-instruct
```

**使用 auto 选模：**

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer sk-aiinfra-xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "messages": [{"role": "user", "content": "简要介绍 AI 中台"}]
  }'
```

**查看路由状态：**

```bash
curl http://localhost:8080/health
# routing_enabled, local_models
curl http://localhost:8080/admin/models -H "Authorization: Bearer <ADMIN_TOKEN>"
# 含 auto、api、local provider 标记
```

### 5.6 自托管推理（Inference + vLLM）

架构：`Gateway → Inference (8082) → vLLM (8000)`

Inference 是 OpenAI 兼容代理，不加载模型。需在本机或 GPU 服务器单独启动 vLLM。

**Step 1 — 启动 vLLM（示例，需 GPU 环境）：**

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --served-model-name qwen2.5-7b-instruct \
  --port 8000
```

**Step 2 — 配置 `.env`：**

```env
LOCAL_MODELS=qwen2.5-7b-instruct
VLLM_BASE_URL=http://localhost:8000/v1
INFERENCE_BASE_URL=http://localhost:8082/v1
```

Docker Compose 中 Inference 默认连接 `host.docker.internal:8000`（宿主机 vLLM）。

**Step 3 — 经 Gateway 调用本地模型：**

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer sk-aiinfra-xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-7b-instruct",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**直接访问 Inference：**

```bash
curl http://localhost:8082/health
curl http://localhost:8082/ready   # 需 vLLM 可达
curl http://localhost:8082/v1/models
```

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 服务健康 |
| GET | `/ready` | vLLM 连通性 |
| POST | `/v1/chat/completions` | 对话补全（转发 vLLM） |
| GET | `/v1/models` | 模型列表 |

### 5.7 Agent 运行时

Agent 服务提供 ReAct 风格工具调用，内置工具：

| 工具 | 说明 |
|------|------|
| `rag_search` | 调用 RAG 检索知识库，参数 `{kb_id, query}` |
| `http_get` | HTTP GET，参数 `{url}` |

**执行 Agent 任务：**

```bash
curl -X POST http://localhost:8083/agents/run \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "根据知识库回答：AI中台的核心价值是什么？",
    "kb_id": 1,
    "max_steps": 6
  }'
```

响应包含 `answer` 与 `steps`（每步工具调用与观察结果）。

**列出可用工具：**

```bash
curl http://localhost:8083/agents/tools \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/health` | 无 | 健康检查 |
| GET | `/ready` | 无 | 就绪检查 |
| GET | `/agents/tools` | Admin Token | 工具列表 |
| POST | `/agents/run` | Admin Token | 执行 Agent |

> Agent 使用 `MODEL_API_KEY` 调用 LLM 做推理，使用 `RAG_INTERNAL_URL` 调用 RAG 检索。

### 5.8 Prompt 管理（P1）

```bash
# 创建模板（含首版内容）
curl -X POST http://localhost:8081/prompts \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "rag-default",
    "tenant_id": "default",
    "content": "你是{{role}}助手，请根据上下文回答。"
  }'

# RAG 问答时指定模板
curl -X POST http://localhost:8081/knowledge-bases/1/chat \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI中台是什么",
    "prompt_template_id": 1,
    "prompt_variables": {"role": "企业知识库"}
  }'

# 配置 A/B（两版本 50/50）
curl -X POST http://localhost:8081/prompts/1/ab \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"variants": [{"version_id": 1, "weight": 50}, {"version_id": 2, "weight": 50}]}'
```

控制台 **Prompt** 页面可可视化管理模板与 A/B。

### 5.9 混合检索（P1）

启用 `.env`：

```env
HYBRID_SEARCH_ENABLED=true
ES_HOST=localhost   # Docker: elasticsearch
ES_PORT=9200
RRF_K=60
```

Docker Compose 已包含 Elasticsearch；新上传文档会双写 Milvus + ES。检索时自动 RRF 融合后再 Rerank。

### 5.10 多租户治理（P1）

```bash
# 创建租户
curl -X POST http://localhost:8080/admin/tenants \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{"id": "team-a", "name": "Team A"}'

# 设置配额（0=不限）
curl -X PUT http://localhost:8080/admin/tenants/team-a/quota \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{"monthly_token_limit": 1000000, "monthly_request_limit": 10000, "kb_limit": 5}'

# 查看用量
curl http://localhost:8080/admin/tenants/team-a/usage \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

控制台「连接设置」可设 **租户过滤**；**租户** 页面管理配额与用量。

已有数据库需执行：`mysql ... < scripts/init_db_p1.sql`

### 5.11 Langfuse Trace（P1）

配置 `.env` 后 Gateway / RAG 自动上报 Trace（未配置则 no-op）：

```env
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

RAG Trace 包含：检索 hits、System Prompt 元信息、LLM 输入输出。

### 5.12 异步入库（P2）

默认 `INGESTION_ASYNC=true`：上传后立即返回 `status: queued`，后台 Redis Worker 处理。

```bash
# 异步上传（默认）
curl -X POST "http://localhost:8081/knowledge-bases/1/documents?async_ingest=true" \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -F "file=@doc.pdf"

# 查询进度
curl http://localhost:8081/knowledge-bases/1/documents/5 \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
# progress: 0-100, status: queued|processing|ready|failed
```

控制台知识库详情页会自动轮询进度条。

### 5.13 增量更新与外部同步（P2）

**同文件名重复上传** → 自动走增量 diff，仅更新变化 chunk。

**Confluence 同步示例：**

```bash
curl -X POST http://localhost:8081/knowledge-bases/1/sync-sources \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "wiki-home",
    "source_type": "confluence",
    "config": {
      "base_url": "https://your.atlassian.net",
      "page_id": "123456",
      "token": "your-api-token"
    },
    "cron_minutes": 60
  }'

curl -X POST http://localhost:8081/knowledge-bases/1/sync-sources/1/run \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

**飞书文档：** `source_type: lark`，config 含 `document_id` 与 `tenant_access_token`。

已有数据库执行：`mysql ... < scripts/init_db_p2.sql`

### 5.14 多模态入库（P2）

支持扩展名：

| 类型 | 格式 | 配置 |
|------|------|------|
| 图片 OCR | png/jpg/webp | `OCR_BACKEND=api` 或 `tesseract` |
| 音频 ASR | mp3/wav/m4a | `ASR_BACKEND=api`（OpenAI Whisper 兼容） |

```env
OCR_BACKEND=api
OCR_VISION_MODEL=gpt-4o-mini
ASR_BACKEND=api
ASR_MODEL=whisper-1
```

本地 OCR：`pip install -r services/rag/requirements-multimodal.txt`，`OCR_BACKEND=tesseract`

### 5.15 TypeScript / Java SDK（P2）

**TypeScript**

```bash
cd sdk/typescript && npm install && npm run build
```

```typescript
import { RagClient } from '@aiinfra/sdk';
const rag = new RagClient('http://localhost:8081', { adminToken: 'xxx' });
await rag.uploadDocument(1, file, 'doc.pdf');
```

**Java**

```bash
mvn -f sdk/java package
```

```java
RagClient rag = new RagClient("http://localhost:8081", adminToken);
JsonNode doc = rag.getDocument(1, 5);
```

### 5.16 MLOps 微调流水线（P3）

```bash
# 创建微调任务
curl -X POST http://localhost:8084/jobs \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{"name":"domain-lora","base_model":"qwen2.5-7b-instruct","tenant_id":"default"}'

# 添加标注样本
curl -X POST http://localhost:8084/jobs/1/samples \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{"instruction":"回答","input_text":"问题","output_text":"答案","label_status":"approved"}'

# 提交训练（异步）
curl -X POST http://localhost:8084/jobs/1/submit -H "Authorization: Bearer <ADMIN_TOKEN>"

# 模型注册表 / 灰度
curl http://localhost:8084/registry -H "Authorization: Bearer <ADMIN_TOKEN>"
curl -X PUT http://localhost:8084/registry/1/canary \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{"canary_weight": 20}'
```

配置真实 LoRA 训练：`LORA_TRAIN_CMD="python scripts/train_lora.py --dataset {dataset} --output {output}"`

Gateway 会根据注册表 `canary_weight` 将流量灰度到 `{name}-{version}` 模型。

### 5.17 Agent 工作流编排（P3）

```bash
curl -X POST http://localhost:8083/workflows \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{
    "name": "rag-qa-flow",
    "definition": {
      "nodes": [
        {"id":"start","type":"start"},
        {"id":"rag","type":"rag","data":{"kb_id":1}},
        {"id":"llm","type":"llm","data":{"prompt":"你是助手"}},
        {"id":"end","type":"end"}
      ],
      "edges": [
        {"source":"start","target":"rag"},
        {"source":"rag","target":"llm"},
        {"source":"llm","target":"end"}
      ]
    }
  }'

curl -X POST http://localhost:8083/workflows/1/run \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{"query":"AI中台是什么？"}'
```

控制台 **Agent 编排** 页面支持拖拽节点布局。

### 5.18 AI 评测平台（P3）

```bash
curl -X POST http://localhost:8081/eval/datasets \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{
    "name": "rag-smoke",
    "items": [{"query":"AI中台是什么","expected":"能力操作系统"}]
  }'

curl -X POST http://localhost:8081/eval/runs \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{
    "dataset_id": 1,
    "name": "hybrid-on",
    "config": {"kb_id": 1, "top_k": 5}
  }'

curl "http://localhost:8081/eval/runs/compare?run_a=1&run_b=2" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

### 5.19 联邦检索（P3）

```bash
curl -X POST http://localhost:8081/federated/chat \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{
    "kb_ids": [1, 2],
    "query": "总结两个知识库的共同点",
    "tenant_id": "default"
  }'
```

仅允许访问 `tenant_id` 匹配的知识库，跨租户请求返回 403。

已有数据库：`mysql ... < scripts/init_db_p3.sql`

---

## 6. RAG 知识库使用

所有 RAG 管理接口使用 **Admin Token**（`Authorization: Bearer <ADMIN_TOKEN>`）。

### 6.1 完整流程

**Step 1 — 创建知识库**

```bash
curl -X POST http://localhost:8081/knowledge-bases \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "产品文档",
    "tenant_id": "team-a",
    "description": "内部产品手册"
  }'
```

**Step 2 — 上传文档**

支持格式：`.txt` `.md` `.markdown` `.csv` `.json` `.pdf`

```bash
curl -X POST http://localhost:8081/knowledge-bases/1/documents \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -F "file=@./README.md"
```

文档上传后自动执行：解析 → 分块 → Embedding → 写入 Milvus。  
可在响应或文档列表中查看 `status`（`ready` / `failed`）和 `chunk_count`。

**Step 3 — 向量检索**

```bash
curl -X POST http://localhost:8081/knowledge-bases/1/retrieve \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"query": "AI中台是什么", "top_k": 5}'
```

**Step 4 — RAG 问答（带引用）**

```bash
curl -X POST http://localhost:8081/knowledge-bases/1/chat \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"query": "AI中台的核心目标是什么？"}'
```

### 6.2 RAG API 列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查（含 embedding/rerank 后端信息） |
| GET | `/ready` | MySQL + Milvus + 本地模型就绪 |
| GET | `/metrics` | Prometheus 指标 |
| POST | `/knowledge-bases` | 创建知识库 |
| GET | `/knowledge-bases` | 列表（`?tenant_id=` 过滤） |
| GET | `/knowledge-bases/{id}` | 详情 |
| DELETE | `/knowledge-bases/{id}` | 删除（含向量与文件） |
| POST | `/knowledge-bases/{id}/documents` | 上传文档 |
| GET | `/knowledge-bases/{id}/documents` | 文档列表 |
| DELETE | `/knowledge-bases/{id}/documents/{doc_id}` | 删除文档 |
| POST | `/knowledge-bases/{id}/retrieve` | 检索 |
| POST | `/knowledge-bases/{id}/chat` | RAG 问答 |

### 6.3 检索链路

```
Query
  → Embedding（BGE-M3 或 OpenAI API）
  → Milvus 召回 Top (RETRIEVAL_K × CANDIDATE_M) 条
  → BGE Reranker 精排（若启用）
  → 取 Top RETRIEVAL_K 条
  → LLM 生成回答 + 返回 sources
```

### 6.4 已有 Phase 1 数据库时追加 RAG 表

若 MySQL 数据卷在 Phase 2 之前已创建，需手动执行：

```bash
mysql -h localhost -u aiinfra -p aiinfra < scripts/init_db_rag.sql
```

---

## 7. 本地 BGE 模型

### 7.1 下载模型

```bash
pip install huggingface_hub
python scripts/download_bge_models.py
```

默认下载到：

- `models/bge-m3`
- `models/bge-reranker-base`

### 7.2 配置 .env

```env
EMBEDDING_BACKEND=bge
RERANK_BACKEND=bge
BGE_M3_PATH=models/bge-m3
BGE_RERANKER_PATH=models/bge-reranker-base
BGE_EMBEDDING_DIMENSION=1024
BGE_DEVICE=cpu
BGE_USE_FP16=false
MILVUS_COLLECTION_NAME=aiinfra_kb_bge
```

| 变量 | 说明 |
|------|------|
| `EMBEDDING_BACKEND` | `auto`：有本地模型则用 BGE，否则 API；`bge`：强制本地；`api`：强制 API |
| `RERANK_BACKEND` | `auto` / `bge` / `off` |
| `BGE_DEVICE` | `cpu` 或 `cuda` |
| `CANDIDATE_M` | 召回倍数，实际召回 `RETRIEVAL_K × CANDIDATE_M` 后再 rerank |

### 7.3 向量维度（重要）

| 模式 | 维度 | 配置项 |
|------|------|--------|
| OpenAI API Embedding | 1536 | `EMBEDDING_DIMENSION` |
| BGE-M3 | 1024 | `BGE_EMBEDDING_DIMENSION` |

**切换 Embedding 后端时必须更换 `MILVUS_COLLECTION_NAME`**，或删除旧 Collection 后重新上传文档，否则报维度冲突错误。

### 7.4 验证

```bash
curl http://localhost:8081/health
```

预期：

```json
{
  "embedding_backend": "bge",
  "rerank_backend": "bge",
  "embedding_dimension": 1024
}
```

---

## 8. Web 管理控制台

### 8.1 Docker 模式

```powershell
.\scripts\start.ps1
```

浏览器访问：**http://localhost:3000**

### 8.2 本地开发模式

```powershell
.\scripts\run_console.ps1
```

浏览器访问：**http://localhost:5173**

### 8.3 连接设置

页面顶部「连接设置」：

| 字段 | Docker 推荐值 | 本地开发推荐值 |
|------|---------------|----------------|
| Admin Token | `.env` 中 `ADMIN_TOKEN` | 同左 |
| Gateway Base URL | `/api/gateway` | `/api/gateway` |
| RAG Base URL | `/api/rag` | `/api/rag` |

### 8.4 功能页面

| 页面 | 功能 |
|------|------|
| 概览 | Gateway / RAG 健康、Embedding 后端、可用模型 |
| API Keys | 创建与查看 Gateway API Key |
| 知识库 | 创建/删除知识库、上传文档、RAG 问答测试 |

---

## 9. Python SDK

### 9.1 安装

```bash
pip install -e sdk/python
```

### 9.2 基本用法

```python
from aiinfra import GatewayClient, RagClient, AgentClient

ADMIN = "change-me-admin-token"

# Gateway — 智能路由
with GatewayClient("http://localhost:8080", api_key="sk-aiinfra-xxx") as client:
    resp = client.chat_completions(
        "auto",  # 自动选模
        [{"role": "user", "content": "Hello"}],
    )
    print(resp)

# Agent
with AgentClient("http://localhost:8083", admin_token=ADMIN) as agent:
    result = agent.run("AI中台是什么？", kb_id=1)
    print(result["answer"])
    print(result["steps"])
```

完整 Gateway + RAG 示例：

```python
from aiinfra import GatewayClient, RagClient

ADMIN = "change-me-admin-token"

# Gateway
with GatewayClient("http://localhost:8080", admin_token=ADMIN) as gw:
    key = gw.create_api_key("my-app", tenant_id="team-a")
    print(key["api_key"])

    # 使用 API Key 对话
    with GatewayClient("http://localhost:8080", api_key=key["api_key"]) as client:
        resp = client.chat_completions(
            "gpt-4o-mini",
            [{"role": "user", "content": "Hello"}],
        )
        print(resp)

# RAG
with RagClient("http://localhost:8081", admin_token=ADMIN) as rag:
    kb = rag.create_knowledge_base("手册", tenant_id="team-a")
    rag.upload_document(kb["id"], "README.md")
    print(rag.chat(kb["id"], "AI中台是什么？"))
```

### 9.3 运行示例

```bash
# 确保服务已启动，ADMIN_TOKEN 与 .env 一致
python sdk/python/examples/basic_usage.py
```

更多说明：[sdk/python/README.md](sdk/python/README.md)

---

## 10. Kubernetes 部署

### 10.1 前置条件

- 已配置 `.env`（含 `MODEL_API_KEY`、`ADMIN_TOKEN`）
- 集群可访问（`kubectl cluster-info`）

### 10.2 一键部署

```powershell
.\scripts\k8s_deploy.ps1
```

或 Linux：

```bash
chmod +x scripts/k8s_deploy.sh scripts/k8s_create_secret.sh
./scripts/k8s_deploy.sh
```

脚本执行：构建镜像 →（kind 时）加载镜像 → 从 `.env` 创建 Secret → `kubectl apply -k deploy/k8s`

### 10.3 分步部署

```bash
# 1. 构建镜像
docker build -f services/gateway/Dockerfile -t aiinfra/gateway:latest .
docker build -f services/rag/Dockerfile -t aiinfra/rag:latest .
docker build -f web/console/Dockerfile -t aiinfra/console:latest .

# 2. kind 加载（如适用）
kind load docker-image aiinfra/gateway:latest
kind load docker-image aiinfra/rag:latest
kind load docker-image aiinfra/console:latest

# 3. 创建 Secret
./scripts/k8s_create_secret.sh

# 4. 部署
kubectl apply -k deploy/k8s
```

### 10.4 查看状态

```bash
kubectl get pods -n aiinfra
kubectl logs -f deployment/gateway -n aiinfra
kubectl logs -f deployment/rag -n aiinfra
```

### 10.5 访问服务

| 服务 | 访问方式 |
|------|----------|
| Console | `http://<node-ip>:30080` |
| Grafana | `http://<node-ip>:30300` |
| Prometheus | `kubectl port-forward svc/prometheus 9090:9090 -n aiinfra` |
| Gateway（集群内） | `http://gateway:8080` |
| RAG（集群内） | `http://rag:8081` |

或使用 port-forward：

```bash
kubectl port-forward svc/console 3000:80 -n aiinfra
kubectl port-forward svc/gateway 8080:8080 -n aiinfra
kubectl port-forward svc/rag 8081:8081 -n aiinfra
```

### 10.6 BGE 模型（K8s）

RAG Pod 挂载 PVC `rag-models`（`/app/models`）。可选方案：

1. **Init Job**：在 Job 中运行 `download_bge_models.py` 写入 PVC
2. **手动拷贝**：`kubectl cp models/bge-m3 rag-pod:/app/models/bge-m3 -n aiinfra`

### 10.7 卸载

```bash
kubectl delete -k deploy/k8s
# 保留 PVC：仅删除 deployment；删 namespace 会删 PVC（取决于 reclaim policy）
kubectl delete namespace aiinfra
```

---

## 11. 监控（Prometheus + Grafana）

### 11.1 Docker Compose

当前 Docker Compose **未包含** Prometheus/Grafana，监控仅在 K8s 部署中默认启用。

本地如需监控，可单独 port-forward K8s 监控组件，或自行添加 Prometheus 到 docker-compose。

### 11.2 K8s 监控

部署完成后：

| 组件 | 说明 |
|------|------|
| Prometheus | 抓取 gateway、rag、inference、agent、milvus 的 `/metrics` |
| Grafana | 预置 Prometheus 数据源 |

**Grafana 登录**

- 地址：`http://<node-ip>:30300`
- 用户名：`admin`
- 密码：`.env` 中 `GRAFANA_ADMIN_PASSWORD`（默认 `admin`）

**Prometheus 查询示例**

```promql
# Gateway 请求速率
rate(http_requests_total{job="gateway"}[5m])

# RAG 请求延迟
http_request_duration_seconds_bucket{job="rag"}
```

可在 Grafana 导入社区 Dashboard（搜索 FastAPI、Milvus）。

### 11.3 指标端点

| 服务 | 路径 |
|------|------|
| Gateway | http://localhost:8080/metrics |
| RAG | http://localhost:8081/metrics |
| Inference | http://localhost:8082/metrics |
| Agent | http://localhost:8083/metrics |
| Milvus | http://localhost:9091/metrics |

---

## 12. 环境变量参考

完整模板见 [.env.example](.env.example)。核心分组如下：

### 大模型

| 变量 | 说明 | 示例 |
|------|------|------|
| `MODEL_API_KEY` | 上游 API Key | `sk-xxx` |
| `MODEL_BASE_URL` | OpenAI 兼容 Base URL | `https://api.openai.com/v1` |
| `MODEL_NAME` | 默认对话模型 | `gpt-4o-mini` |

### MySQL

| 变量 | 说明 |
|------|------|
| `MYSQL_HOST` | Docker 内用 `mysql`，本地用 `localhost` |
| `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DATABASE` | 数据库连接 |

### Redis

| 变量 | 说明 |
|------|------|
| `REDIS_HOST` | Docker 内用 `redis` |
| `REDIS_PORT` | 默认 `6379` |

### Milvus / MinIO

| 变量 | 说明 |
|------|------|
| `MILVUS_HOST` | Docker 内用 `milvus` |
| `MILVUS_COLLECTION_NAME` | 向量集合名，换 Embedding 后端时需更换 |
| `MINIO_ENDPOINT` | Docker 内用 `minio:9000` |

### Embedding / BGE

| 变量 | 说明 |
|------|------|
| `EMBEDDING_BACKEND` | `auto` / `api` / `bge` |
| `EMBEDDING_MODEL` | API 模式模型名 |
| `EMBEDDING_DIMENSION` | API 向量维度（1536） |
| `BGE_M3_PATH` | 本地 BGE-M3 路径 |
| `BGE_RERANKER_PATH` | 本地 Reranker 路径 |
| `BGE_EMBEDDING_DIMENSION` | BGE 向量维度（1024） |
| `RERANK_BACKEND` | `auto` / `bge` / `off` |
| `BGE_DEVICE` | `cpu` / `cuda` |

### 网关 / 安全

| 变量 | 说明 |
|------|------|
| `ADMIN_TOKEN` | 管理 API 与控制台鉴权 |
| `DEFAULT_RATE_LIMIT_RPM` | 每 Key 每分钟请求上限 |
| `GATEWAY_PORT` | 默认 8080 |
| `RAG_PORT` | 默认 8081 |
| `CONSOLE_PORT` | 默认 3000 |
| `CORS_ORIGINS` | 控制台跨域来源 |

### 智能路由（P0）

| 变量 | 说明 | 默认 |
|------|------|------|
| `ROUTING_ENABLED` | 是否启用 `model=auto` | `true` |
| `ROUTING_TOKEN_THRESHOLD` | 超过此估算 token 数走复杂模型 | `2000` |
| `ROUTING_SIMPLE_MODEL` | 简单任务模型 | `gpt-4o-mini` |
| `ROUTING_COMPLEX_MODEL` | 复杂任务模型 | `gpt-4o` |
| `FALLBACK_MODEL` | 上游失败时的备用模型 | `gpt-4o-mini` |
| `LOCAL_MODELS` | 逗号分隔，走 Inference 的本地模型名 | — |

### 自托管推理（P0）

| 变量 | 说明 |
|------|------|
| `INFERENCE_PORT` | Inference 端口，默认 8082 |
| `INFERENCE_BASE_URL` | Gateway 访问 Inference 的 URL |
| `INFERENCE_API_KEY` | Inference 鉴权 Key（本地可填 `local`） |
| `VLLM_BASE_URL` | vLLM OpenAI API 地址 |
| `VLLM_API_KEY` | vLLM API Key（多数本地部署填 `empty`） |

### Agent（P0）

| 变量 | 说明 |
|------|------|
| `AGENT_PORT` | Agent 端口，默认 8083 |
| `AGENT_MAX_STEPS` | ReAct 最大步数 |
| `RAG_INTERNAL_URL` | Agent 内部调用 RAG 的地址 |

### 检索参数

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CHILD_CHUNK_SIZE` | 300 | 分块大小 |
| `CHUNK_OVERLAP` | 50 | 分块重叠 |
| `RETRIEVAL_K` | 5 | 最终返回条数 |
| `CANDIDATE_M` | 2 | 召回倍数 |

---

## 13. API 速查

### 鉴权方式

| 场景 | Header |
|------|--------|
| 业务调用 Gateway | `Authorization: Bearer <API Key>` |
| 管理 Gateway / RAG / Agent | `Authorization: Bearer <ADMIN_TOKEN>` |

### 端口与文档

| 服务 | 端口 | Swagger |
|------|------|---------|
| Gateway | 8080 | /docs |
| RAG | 8081 | /docs |
| Inference | 8082 | /docs |
| Agent | 8083 | /docs |
| Console | 3000 / 5173 | — |

---

## 14. 常见问题

### Q1：`ModuleNotFoundError: No module named 'common'`

**原因**：`PYTHONPATH` 未包含项目根目录。

**解决**：使用 `scripts/run_gateway.py` 或 `scripts/run_rag.py` 启动；或手动设置：

```bash
export PYTHONPATH=/path/to/AI-Infra
```

---

### Q2：RAG `/ready` 失败，Milvus 连接错误

**原因**：Milvus 尚未完全启动。

**解决**：

```bash
cd deploy/docker-compose
docker compose logs milvus -f
# 等待 healthcheck 通过后再访问
curl http://localhost:8081/ready
```

---

### Q3：Milvus collection dim 冲突

**错误示例**：`Milvus collection 'aiinfra_kb' dim=1536, expected 1024`

**原因**：API Embedding 与 BGE 向量维度不同，共用了同一 Collection。

**解决**：

1. 修改 `.env`：`MILVUS_COLLECTION_NAME=aiinfra_kb_bge`
2. 重启 RAG，重新上传文档

或删除旧 Collection（开发环境）：

```bash
# 通过 pymilvus 或重启 milvus 数据卷
docker compose down -v  # ⚠️ 清空所有数据
```

---

### Q4：文档上传 `status: failed`

**排查**：

```bash
# 查看 RAG 日志
docker compose logs rag -f
# 或
tail -f logs/app.log
```

常见原因：

- 不支持的文件格式
- `MODEL_API_KEY` 未配置（API Embedding 模式）
- BGE 模型路径不存在（bge 模式）
- PDF 解析失败（空文件或扫描件）

---

### Q5：Gateway 返回 502 Upstream error

**原因**：上游 LLM API 不可达或 Key 无效。

**解决**：

1. 检查 `.env` 中 `MODEL_API_KEY`、`MODEL_BASE_URL`
2. 确认网络可访问上游 API
3. 查看 `logs/app.log` 中详细错误

---

### Q6：控制台无法连接 Gateway / RAG

**排查**：

1. 确认服务已启动：`curl http://localhost:8080/health`
2. 检查控制台「连接设置」中 Admin Token 是否与 `.env` 一致
3. 本地开发确认 Vite 代理配置（`web/console/vite.config.js`）
4. Docker 模式访问 http://localhost:3000（非 5173）

---

### Q7：BGE 模型加载慢 / 内存不足

**建议**：

- 开发机内存 ≥ 16 GB
- 无 GPU 时保持 `BGE_DEVICE=cpu`
- 仅 RAG 服务加载模型，Gateway 不需要 BGE 依赖
- Docker 给容器分配足够内存（Docker Desktop → Resources）

---

### Q8：K8s Pod 镜像拉取失败

**原因**：使用本地构建镜像 `aiinfra/gateway:latest`，集群无法从远程拉取。

**解决**：

```bash
# kind
kind load docker-image aiinfra/gateway:latest

# minikube
minikube image load aiinfra/gateway:latest

# 或推送至集群可访问的镜像仓库并修改 deploy/k8s/kustomization.yaml
```

---

### Q9：如何重置全部数据

```bash
cd deploy/docker-compose
docker compose down -v
rm -rf data/* logs/*
# 重新启动
cd ../..
./scripts/start.sh
```

### Q10：Inference `/ready` 失败

**原因**：vLLM 未启动或 `VLLM_BASE_URL` 配置错误。

**解决**：

1. 确认 vLLM 在对应地址运行：`curl http://localhost:8000/v1/models`
2. Docker 模式下 vLLM 在宿主机时，保持 `VLLM_BASE_URL=http://host.docker.internal:8000/v1`
3. 仅使用 API 模型、不需要本地推理时，可不启动 vLLM；Gateway 调用 `LOCAL_MODELS` 时会失败并触发 Fallback

---

### Q11：Agent 返回「未检索到相关内容」

**原因**：知识库无文档或 `kb_id` 错误。

**解决**：先按第 6 节创建知识库并上传文档，确认 `status: ready` 后再调用 Agent。

---

## 附录：脚本一览

| 脚本 | 说明 |
|------|------|
| `scripts/start.ps1` / `start.sh` | Docker Compose 一键启动 |
| `scripts/run_gateway.py` | 本地启动 Gateway |
| `scripts/run_rag.py` | 本地启动 RAG |
| `scripts/run_inference.py` | 本地启动 Inference 代理 |
| `scripts/run_agent.py` | 本地启动 Agent |
| `scripts/run_console.ps1` / `run_console.sh` | 本地启动控制台 |
| `scripts/download_bge_models.py` | 下载 BGE 模型 |
| `scripts/k8s_deploy.ps1` / `k8s_deploy.sh` | K8s 一键部署 |
| `scripts/k8s_create_secret.ps1` / `k8s_create_secret.sh` | 从 .env 创建 K8s Secret |
| `scripts/init_db.sql` | MySQL 全量初始化 |
| `scripts/init_db_rag.sql` | RAG 表增量迁移 |
| `scripts/init_db_p1.sql` | P1 表与 usage_logs.tenant_id 迁移 |
| `scripts/init_db_p2.sql` | P2 异步/同步/增量表迁移 |
| `scripts/init_db_p3.sql` | P3 MLOps/评测/工作流/联邦表迁移 |

---

## 附录：日志位置

| 类型 | 路径 |
|------|------|
| 应用日志 | `logs/app.log` |
| Docker 容器日志 | `docker compose logs <service> -f` |
| K8s Pod 日志 | `kubectl logs -f deployment/<name> -n aiinfra` |

---

*文档随项目迭代更新，如有疑问请先查阅本文档第 14 节「常见问题」。*
