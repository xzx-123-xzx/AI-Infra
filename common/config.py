import json
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

from common.path_utils import get_file_path

# 加载 .env 文件，指定 encoding='utf-8' 避免编码问题
_env_path = get_file_path(f".env")
if os.path.exists(_env_path):
    # 尝试用 utf-8 加载，失败则用 gbk
    try:
        with open(_env_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(_env_path, 'r', encoding='gbk') as f:
            content = f.read()
        # 将 GBK 编码的内容重新写入为 UTF-8
        with open(_env_path, 'w', encoding='utf-8') as f:
            f.write(content)
    load_dotenv(_env_path, encoding='utf-8')


def _int(key: str, default: int = 0) -> int:
    val = os.getenv(key)
    return int(val) if val is not None else default


def _str(key: str, default: str = "") -> str:
    return os.getenv(key) or default


class Config:
    def __init__(self):
        # 大模型相关
        self.MODEL_API_KEY = _str("MODEL_API_KEY")
        self.MODEL_BASE_URL = _str("MODEL_BASE_URL")
        self.MODEL_NAME = _str("MODEL_NAME")

        # MySQL
        self.MYSQL_HOST = _str("MYSQL_HOST", "localhost")
        self.MYSQL_USER = _str("MYSQL_USER")
        self.MYSQL_PASSWORD = _str("MYSQL_PASSWORD")
        self.MYSQL_DATABASE = _str("MYSQL_DATABASE")

        # Redis
        self.REDIS_HOST = _str("REDIS_HOST", "localhost")
        self.REDIS_PORT = _int("REDIS_PORT", 6379)
        self.REDIS_PASSWORD = _str("REDIS_PASSWORD")
        self.REDIS_DB = _int("REDIS_DB", 0)
        self.REDIS_EXPIRE = _int("REDIS_EXPIRE", 86400)

        # Milvus
        self.MILVUS_HOST = _str("MILVUS_HOST", "localhost")
        self.MILVUS_PORT = _int("MILVUS_PORT", 19530)
        self.MILVUS_DATABASE_NAME = _str("MILVUS_DATABASE_NAME", "default")
        self.MILVUS_COLLECTION_NAME = _str("MILVUS_COLLECTION_NAME", "aiinfra_kb")

        # 检索参数
        self.PARENT_CHUNK_SIZE = _int("PARENT_CHUNK_SIZE", 1200)
        self.CHILD_CHUNK_SIZE = _int("CHILD_CHUNK_SIZE", 300)
        self.CHUNK_OVERLAP = _int("CHUNK_OVERLAP", 50)
        self.RETRIEVAL_K = _int("RETRIEVAL_K", 5)
        self.CANDIDATE_M = _int("CANDIDATE_M", 2)

        # 本地模型路径
        self.BGE_M3_PATH = _str("BGE_M3_PATH")
        self.BGE_RERANKER_PATH = _str("BGE_RERANKER_PATH")
        self.EMBEDDING_BACKEND = _str("EMBEDDING_BACKEND", "auto").lower()
        self.RERANK_BACKEND = _str("RERANK_BACKEND", "auto").lower()
        self.BGE_DEVICE = _str("BGE_DEVICE", "cpu")
        self.BGE_BATCH_SIZE = _int("BGE_BATCH_SIZE", 12)
        self.BGE_USE_FP16 = _str("BGE_USE_FP16", "false").lower() == "true"
        self.BGE_EMBEDDING_DIMENSION = _int("BGE_EMBEDDING_DIMENSION", 1024)
        self.BGE_RERANK_BATCH_SIZE = _int("BGE_RERANK_BATCH_SIZE", 32)
        self.BERT_BASE_PATH = _str("BERT_BASE_PATH")
        self.DOCUMENT_SEGMENTATION_PATH = _str("DOCUMENT_SEGMENTATION_PATH")
        self.BERT_CLASSIFIER_PATH = get_file_path("models/bert_classifier")

        # 日志
        self.LOG_FILE = get_file_path("logs/app.log")

        self.ORIGIN_MODEL_PATH= _str("ORIGIN_MODEL_PATH")

        # 应用配置
        _sources = _str("VALID_SOURCES")
        self.VALID_SOURCES = json.loads(_sources) if _sources else ["ai", "java", "test", "ops", "bigdata"]
        self.CUSTOMER_SERVICE_PHONE = _str("CUSTOMER_SERVICE_PHONE")

        # 网关
        self.APP_NAME = _str("APP_NAME", "AI-Infra Gateway")
        self.GATEWAY_HOST = _str("GATEWAY_HOST", "0.0.0.0")
        self.GATEWAY_PORT = _int("GATEWAY_PORT", 8080)
        self.ADMIN_TOKEN = _str("ADMIN_TOKEN", "change-me-admin-token")
        self.DEFAULT_RATE_LIMIT_RPM = _int("DEFAULT_RATE_LIMIT_RPM", 60)
        self.AVAILABLE_MODELS = _str("AVAILABLE_MODELS")

        # 智能路由（P0）
        self.ROUTING_ENABLED = _str("ROUTING_ENABLED", "true").lower() == "true"
        self.ROUTING_TOKEN_THRESHOLD = _int("ROUTING_TOKEN_THRESHOLD", 2000)
        self.ROUTING_SIMPLE_MODEL = _str("ROUTING_SIMPLE_MODEL") or self.MODEL_NAME
        self.ROUTING_COMPLEX_MODEL = _str("ROUTING_COMPLEX_MODEL") or "gpt-4o"
        self.FALLBACK_MODEL = _str("FALLBACK_MODEL") or self.ROUTING_SIMPLE_MODEL
        _local = _str("LOCAL_MODELS")
        self.LOCAL_MODELS = [m.strip() for m in _local.split(",") if m.strip()] if _local else []

        # 自托管推理（P0）
        self.INFERENCE_APP_NAME = _str("INFERENCE_APP_NAME", "AI-Infra Inference")
        self.INFERENCE_HOST = _str("INFERENCE_HOST", "0.0.0.0")
        self.INFERENCE_PORT = _int("INFERENCE_PORT", 8082)
        self.INFERENCE_BASE_URL = _str("INFERENCE_BASE_URL", "http://localhost:8082/v1")
        self.INFERENCE_API_KEY = _str("INFERENCE_API_KEY", "local")
        self.VLLM_BASE_URL = _str("VLLM_BASE_URL", "http://localhost:8000/v1")
        self.VLLM_API_KEY = _str("VLLM_API_KEY", "empty")

        # Agent 服务（P0）
        self.AGENT_APP_NAME = _str("AGENT_APP_NAME", "AI-Infra Agent")
        self.AGENT_HOST = _str("AGENT_HOST", "0.0.0.0")
        self.AGENT_PORT = _int("AGENT_PORT", 8083)
        self.AGENT_MAX_STEPS = _int("AGENT_MAX_STEPS", 6)
        self.RAG_INTERNAL_URL = _str("RAG_INTERNAL_URL", "http://localhost:8081")

        # RAG 服务
        self.RAG_APP_NAME = _str("RAG_APP_NAME", "AI-Infra RAG")
        self.RAG_HOST = _str("RAG_HOST", "0.0.0.0")
        self.RAG_PORT = _int("RAG_PORT", 8081)
        self.EMBEDDING_MODEL = _str("EMBEDDING_MODEL", "text-embedding-3-small")
        self.EMBEDDING_DIMENSION = _int("EMBEDDING_DIMENSION", 1536)
        self.KB_DATA_DIR = get_file_path("data/knowledge_bases")

        # MinIO（文档对象存储，可选）
        self.MINIO_ENDPOINT = _str("MINIO_ENDPOINT", "localhost:9000")
        self.MINIO_ACCESS_KEY = _str("MINIO_ACCESS_KEY", "minioadmin")
        self.MINIO_SECRET_KEY = _str("MINIO_SECRET_KEY", "minioadmin")
        self.MINIO_BUCKET = _str("MINIO_BUCKET", "aiinfra")
        self.MINIO_SECURE = _str("MINIO_SECURE", "false").lower() == "true"

        # 控制台
        self.CONSOLE_PORT = _int("CONSOLE_PORT", 3000)
        _cors = _str("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
        self.CORS_ORIGINS = [item.strip() for item in _cors.split(",") if item.strip()]

        # 混合检索（P1）
        self.HYBRID_SEARCH_ENABLED = _str("HYBRID_SEARCH_ENABLED", "false").lower() == "true"
        self.ES_HOST = _str("ES_HOST", "localhost")
        self.ES_PORT = _int("ES_PORT", 9200)
        self.ES_INDEX_PREFIX = _str("ES_INDEX_PREFIX", "aiinfra_chunks")
        self.RRF_K = _int("RRF_K", 60)

        # Prompt 默认（P1）
        self.DEFAULT_RAG_SYSTEM_PROMPT = _str(
            "DEFAULT_RAG_SYSTEM_PROMPT",
            "你是企业知识库问答助手。请仅根据提供的上下文回答问题。\n"
            "如果上下文不足以回答，请明确说明不知道，不要编造。\n"
            "回答时引用相关事实，保持简洁准确。",
        )

        # Langfuse Trace（P1）
        self.LANGFUSE_PUBLIC_KEY = _str("LANGFUSE_PUBLIC_KEY")
        self.LANGFUSE_SECRET_KEY = _str("LANGFUSE_SECRET_KEY")
        self.LANGFUSE_HOST = _str("LANGFUSE_HOST", "https://cloud.langfuse.com")

        # 异步入库（P2）
        self.INGESTION_ASYNC = _str("INGESTION_ASYNC", "true").lower() == "true"
        self.INGESTION_WORKER_ENABLED = _str("INGESTION_WORKER_ENABLED", "true").lower() == "true"
        self.SYNC_WORKER_INTERVAL = _int("SYNC_WORKER_INTERVAL", 300)

        # 多模态（P2）
        self.OCR_BACKEND = _str("OCR_BACKEND", "off").lower()  # off | api | tesseract
        self.ASR_BACKEND = _str("ASR_BACKEND", "api").lower()  # off | api
        self.OCR_VISION_MODEL = _str("OCR_VISION_MODEL", "gpt-4o-mini")
        self.ASR_MODEL = _str("ASR_MODEL", "whisper-1")

        # MLOps（P3）
        self.MLOPS_APP_NAME = _str("MLOPS_APP_NAME", "AI-Infra MLOps")
        self.MLOPS_HOST = _str("MLOPS_HOST", "0.0.0.0")
        self.MLOPS_PORT = _int("MLOPS_PORT", 8084)
        self.MLOPS_DATA_DIR = get_file_path("data/mlops")
        self.LORA_TRAIN_CMD = _str("LORA_TRAIN_CMD")
        self.MLOPS_WORKER_ENABLED = _str("MLOPS_WORKER_ENABLED", "true").lower() == "true"

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.LANGFUSE_PUBLIC_KEY and self.LANGFUSE_SECRET_KEY)

    @property
    def es_url(self) -> str:
        return f"http://{self.ES_HOST}:{self.ES_PORT}"

    def embedding_url(self) -> str:
        base = self.MODEL_BASE_URL.rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/embeddings"
        return f"{base}/v1/embeddings"

    def resolve_path(self, path: str) -> str:
        if not path:
            return ""
        if os.path.isabs(path):
            return path
        return get_file_path(path)

    def model_dir_ready(self, path: str) -> bool:
        resolved = self.resolve_path(path)
        if not resolved or not os.path.isdir(resolved):
            return False
        markers = ("config.json", "pytorch_model.bin", "model.safetensors")
        return any(os.path.exists(os.path.join(resolved, name)) for name in markers)

    @property
    def mysql_url(self) -> str:
        password = quote_plus(self.MYSQL_PASSWORD) if self.MYSQL_PASSWORD else ""
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{password}"
            f"@{self.MYSQL_HOST}:3306/{self.MYSQL_DATABASE}?charset=utf8mb4"
        )

    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            password = quote_plus(self.REDIS_PASSWORD)
            return f"redis://:{password}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def model_list(self) -> list[str]:
        raw = self.AVAILABLE_MODELS or self.MODEL_NAME
        return [m.strip() for m in raw.split(",") if m.strip()]

    @property
    def use_local_embedding(self) -> bool:
        if self.EMBEDDING_BACKEND == "api":
            return False
        if self.EMBEDDING_BACKEND == "bge":
            return True
        return self.model_dir_ready(self.BGE_M3_PATH)

    @property
    def use_local_rerank(self) -> bool:
        if self.RERANK_BACKEND == "off":
            return False
        if self.RERANK_BACKEND == "bge":
            return True
        return self.model_dir_ready(self.BGE_RERANKER_PATH)

    @property
    def embedding_dimension(self) -> int:
        if self.use_local_embedding:
            return self.BGE_EMBEDDING_DIMENSION
        return self.EMBEDDING_DIMENSION

    @property
    def retrieval_candidates(self) -> int:
        return max(self.RETRIEVAL_K * self.CANDIDATE_M, self.RETRIEVAL_K)

    @property
    def local_model_set(self) -> set[str]:
        return set(self.LOCAL_MODELS)

    @property
    def cors_origins(self) -> list[str]:
        return self.CORS_ORIGINS


conf = Config()


if __name__ == "__main__":
    #print(conf.BERT_BASE_PATH)
    # print(conf.MODEL_API_KEY)
    # print(conf.MODEL_BASE_URL)
    # print(conf.MODEL_NAME)
    print(conf.ORIGIN_MODEL_PATH)
