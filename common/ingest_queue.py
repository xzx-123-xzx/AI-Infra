"""Redis 文档入库任务队列。"""

from __future__ import annotations

import json

import redis

from common.config import conf

QUEUE_KEY = "aiinfra:ingest:queue"
_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(conf.redis_url, decode_responses=True)
    return _redis


def enqueue_ingest(doc_id: int, *, incremental: bool = False) -> None:
    payload = json.dumps({"doc_id": doc_id, "incremental": incremental})
    get_redis().rpush(QUEUE_KEY, payload)


def dequeue_ingest(timeout: int = 5) -> dict | None:
    item = get_redis().blpop(QUEUE_KEY, timeout=timeout)
    if not item:
        return None
    return json.loads(item[1])


def queue_length() -> int:
    return int(get_redis().llen(QUEUE_KEY))
