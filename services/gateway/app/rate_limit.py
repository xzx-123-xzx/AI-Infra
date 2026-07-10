import time

import redis
from fastapi import HTTPException, status

from common.config import conf

_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(conf.redis_url, decode_responses=True)
    return _redis


def check_rate_limit(api_key_id: int, limit_rpm: int) -> None:
    client = get_redis()
    window = int(time.time() // 60)
    key = f"rate:{api_key_id}:{window}"
    count = client.incr(key)
    if count == 1:
        client.expire(key, 120)
    if count > limit_rpm:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {limit_rpm} requests per minute",
        )
