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
    def cors_origins(self) -> list[str]:
        return self.CORS_ORIGINS


conf = Config()


if __name__ == "__main__":
    #print(conf.BERT_BASE_PATH)
    # print(conf.MODEL_API_KEY)
    # print(conf.MODEL_BASE_URL)
    # print(conf.MODEL_NAME)
    print(conf.ORIGIN_MODEL_PATH)
