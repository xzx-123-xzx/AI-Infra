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
| rag | RAG 服务 :8081 |
| console | Web 管理台 :3000 |

### 3.3 验证

```bash
# Gateway
curl http://localhost:8080/health

# RAG
curl http://localhost:8081/health

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

### 4.4 启动控制台（前端热更新）

```powershell
# 需 gateway + rag 已运行
.\scripts\run_console.ps1
# 或 ./scripts/run_console.sh
```

访问：http://localhost:5173（Vite 开发服务器，自动代理 `/api/gateway` 和 `/api/rag`）

### 4.5 PYTHONPATH 说明

`run_gateway.py` / `run_rag.py` 已自动设置：

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
| Prometheus | 抓取 gateway:8080、rag:8081、milvus:9091 的 `/metrics` |
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
| 管理 Gateway / RAG | `Authorization: Bearer <ADMIN_TOKEN>` |

### 端口与文档

| 服务 | 端口 | Swagger |
|------|------|---------|
| Gateway | 8080 | /docs |
| RAG | 8081 | /docs |
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

---

## 附录：脚本一览

| 脚本 | 说明 |
|------|------|
| `scripts/start.ps1` / `start.sh` | Docker Compose 一键启动 |
| `scripts/run_gateway.py` | 本地启动 Gateway |
| `scripts/run_rag.py` | 本地启动 RAG |
| `scripts/run_console.ps1` / `run_console.sh` | 本地启动控制台 |
| `scripts/download_bge_models.py` | 下载 BGE 模型 |
| `scripts/k8s_deploy.ps1` / `k8s_deploy.sh` | K8s 一键部署 |
| `scripts/k8s_create_secret.ps1` / `k8s_create_secret.sh` | 从 .env 创建 K8s Secret |
| `scripts/init_db.sql` | MySQL 全量初始化 |
| `scripts/init_db_rag.sql` | RAG 表增量迁移 |

---

## 附录：日志位置

| 类型 | 路径 |
|------|------|
| 应用日志 | `logs/app.log` |
| Docker 容器日志 | `docker compose logs <service> -f` |
| K8s Pod 日志 | `kubectl logs -f deployment/<name> -n aiinfra` |

---

*文档随项目迭代更新，如有疑问请先查阅本文档第 14 节「常见问题」。*
