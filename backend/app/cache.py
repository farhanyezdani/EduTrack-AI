"""Small Redis cache-aside helper. Everything is a no-op when REDIS_URL is unset."""
import json
import logging

import redis

from app.config import settings

log = logging.getLogger(__name__)
_client: redis.Redis | None = None
if settings.redis_url:
    _client = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=1)

PREFIX = "edutrack:"


def get_json(key: str):
    if not _client:
        return None
    try:
        raw = _client.get(PREFIX + key)
        return json.loads(raw) if raw else None
    except redis.RedisError as e:
        log.warning("Redis get failed: %s", e)
        return None


def set_json(key: str, value, ttl: int = 300):
    if not _client:
        return
    try:
        _client.setex(PREFIX + key, ttl, json.dumps(value, default=str))
    except redis.RedisError as e:
        log.warning("Redis set failed: %s", e)


def invalidate():
    if not _client:
        return
    try:
        keys = list(_client.scan_iter(PREFIX + "*"))
        if keys:
            _client.delete(*keys)
    except redis.RedisError as e:
        log.warning("Redis invalidate failed: %s", e)


def status() -> str:
    if not _client:
        return "disabled"
    try:
        _client.ping()
        return "connected"
    except redis.RedisError:
        return "unreachable"
