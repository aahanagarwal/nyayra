"""Shared singletons.

The key pool MUST be process-wide. Per-module pools each keep their own
cooldown state, so a key cooled by one route stays "live" to every other route
and gets re-hit until it 429s again — rotation silently stops working. One pool,
one source of truth.
"""

from functools import lru_cache

from app.clients.gemini import GeminiClient
from app.clients.keypool import KeyPool
from app.core.config import Settings, get_settings
from app.retrieval.base import Retriever
from app.retrieval.curated import get_retriever as _get_retriever


@lru_cache(maxsize=1)
def get_pool() -> KeyPool:
    return KeyPool.from_values(get_settings().key_list)


@lru_cache(maxsize=1)
def get_client() -> GeminiClient:
    settings = get_settings()
    return GeminiClient(get_pool(), max_concurrent=settings.max_concurrent_calls)


def get_retriever() -> Retriever:
    return _get_retriever()


def get_config() -> Settings:
    return get_settings()
