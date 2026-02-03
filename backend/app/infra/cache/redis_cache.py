from __future__ import annotations

import json
from typing import Any, Optional

import redis


class RedisCache:
    def __init__(self, url: str) -> None:
        self.url = url
        self.client: Optional[redis.Redis] = None

    def connect(self) -> None:
        if self.client is None:
            self.client = redis.Redis.from_url(self.url, decode_responses=True)

    def close(self) -> None:
        if self.client is not None:
            self.client.close()
            self.client = None

    def get_json(self, key: str) -> Optional[dict]:
        if self.client is None:
            return None
        value = self.client.get(key)
        if value is None:
            return None
        return json.loads(value)

    def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        if self.client is None:
            return
        payload = json.dumps(value, default=str)
        if ttl is None:
            self.client.set(key, payload)
        else:
            self.client.setex(key, ttl, payload)

    def set_bytes(self, key: str, value: bytes, ttl: int | None = None) -> None:
        if self.client is None:
            return
        if ttl is None:
            self.client.set(key, value)
        else:
            self.client.setex(key, ttl, value)

    def get_bytes(self, key: str) -> Optional[bytes]:
        if self.client is None:
            return None
        return self.client.get(key)
