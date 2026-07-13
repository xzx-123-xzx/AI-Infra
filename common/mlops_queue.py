"""MLOps 微调任务 Redis 队列。"""

from __future__ import annotations

import json

import redis

from common.config import conf

QUEUE_KEY = "aiinfra:mlops:queue"
_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(conf.redis_url, decode_responses=True)
    return _redis


def enqueue_job(job_id: int) -> None:
    get_redis().rpush(QUEUE_KEY, json.dumps({"job_id": job_id}))


def dequeue_job(timeout: int = 5) -> dict | None:
    item = get_redis().blpop(QUEUE_KEY, timeout=timeout)
    if not item:
        return None
    return json.loads(item[1])
