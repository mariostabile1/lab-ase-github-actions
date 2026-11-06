"""Bonus stage only: Redis replaces last.json *inside the history service*."""
import json
import os
import redis

_client = redis.Redis(
    host=os.environ.get("REDIS_HOST", "db"),
    port=6379,
    decode_responses=True,
    socket_connect_timeout=3,
    socket_timeout=3,
)


def save_last(operation):
    _client.set("last", json.dumps(operation))


def load_last():
    value = _client.get("last")
    return None if value is None else json.loads(value)
