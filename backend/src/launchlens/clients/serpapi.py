"""Thin client for SerpApi — the DEMAND side (what the market wants).

One function, `search(engine, params)`, covers every SerpApi engine we use
(google_trends, google_shopping, google_news, google). Live-only: a SerpApi key
is required.
"""
import logging

import requests

from .. import config

logger = logging.getLogger(__name__)


def search(engine: str, params: dict) -> dict:
    """Run one SerpApi query and return the parsed JSON response.

    engine: "google_trends" | "google_shopping" | "google_news" | "google"
    params: engine-specific query params (q, geo, gl, hl, data_type, ...)
    """
    if not config.SERPAPI_API_KEY:
        raise RuntimeError("SERPAPI_API_KEY is not set — add it to your .env")

    query = {**params, "engine": engine, "api_key": config.SERPAPI_API_KEY}
    logger.info("serpapi live call: %s %s", engine, params.get("q", ""))
    response = requests.get(config.SERPAPI_URL, params=query, timeout=60)
    response.raise_for_status()
    return response.json()
