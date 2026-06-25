"""Checkpointer factory — short-term memory that survives restarts.

Redis is the primary backend (cloud or local). If REDIS_URI is empty or the
connection/setup fails, we fall back to SQLite so the app always runs. The graph
never knows which backend it got — that is the point of the checkpointer interface.
"""
import logging
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from . import config

logger = logging.getLogger(__name__)

# Context managers / connections kept open for the process lifetime.
_open_cms: list = []
_open_conns: list = []


def get_checkpointer():
    """Return an active checkpointer (Redis if configured & reachable, else SQLite)."""
    if config.REDIS_URI:
        try:
            from langgraph.checkpoint.redis import RedisSaver

            cm = RedisSaver.from_conn_string(config.REDIS_URI)
            saver = cm.__enter__()
            saver.setup()  # create indices on first use
            _open_cms.append(cm)
            logger.info("checkpointer: Redis")
            return saver
        except Exception as exc:  # noqa: BLE001 - any Redis failure → fall back
            logger.warning("Redis unavailable (%s); falling back to SQLite", exc)

    conn = sqlite3.connect(config.SQLITE_PATH, check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    _open_conns.append(conn)
    logger.info("checkpointer: SQLite (%s)", config.SQLITE_PATH)
    return saver


def get_store():
    """Return a long-term, cross-thread Store for facts that outlive a single thread.

    Redis-backed if REDIS_URI is set & reachable (facts persist across restarts AND
    across every thread); otherwise an in-memory store so the graph still runs.
    """
    if config.REDIS_URI:
        try:
            from langgraph.store.redis import RedisStore

            cm = RedisStore.from_conn_string(config.REDIS_URI)
            store = cm.__enter__()
            store.setup()  # create store indices on first use
            _open_cms.append(cm)
            logger.info("store: Redis (long-term, cross-thread)")
            return store
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis store unavailable (%s); using in-memory store", exc)

    from langgraph.store.memory import InMemoryStore

    logger.info("store: in-memory (not persistent across restarts)")
    return InMemoryStore()


def close() -> None:
    """Release Redis connections / SQLite handles on shutdown."""
    for cm in _open_cms:
        try:
            cm.__exit__(None, None, None)
        except Exception:  # noqa: BLE001
            pass
    for conn in _open_conns:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass
    _open_cms.clear()
    _open_conns.clear()


def list_threads(checkpointer) -> list[str]:
    """Best-effort list of known thread_ids in the checkpointer."""
    seen: list[str] = []
    try:
        for cp in checkpointer.list(None):
            tid = cp.config.get("configurable", {}).get("thread_id")
            if tid and tid not in seen:
                seen.append(tid)
    except Exception:  # noqa: BLE001 - listing is optional
        logger.info("thread listing not available for this backend")
    return seen
