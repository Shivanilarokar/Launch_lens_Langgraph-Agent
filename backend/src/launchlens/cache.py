"""Tiny on-disk response cache (token & cost discipline).

Repeat questions in a session — or across runs — should not re-spend the SerpApi
~250/month free tier or Oxylabs credits. Keyed by a hash of the request, stored as
JSON under .cache/ with a TTL. Disabled with CACHE_ENABLED=false.
"""
import hashlib
import json
import logging
import time

from . import config

logger = logging.getLogger(__name__)


def _path(key: str):
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]
    return config.CACHE_DIR / f"{digest}.json"


def get(key: str):
    """Return the cached value for `key`, or None if missing/expired/disabled."""
    if not config.CACHE_ENABLED:
        return None
    path = _path(key)
    if not path.exists():
        return None
    if config.CACHE_TTL and (time.time() - path.stat().st_mtime) > config.CACHE_TTL:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def set(key: str, value) -> None:
    """Store `value` under `key`. Cache failures are non-fatal."""
    if not config.CACHE_ENABLED:
        return
    try:
        _path(key).write_text(json.dumps(value), encoding="utf-8")
    except (OSError, TypeError):
        logger.debug("cache write failed for %s", key)
