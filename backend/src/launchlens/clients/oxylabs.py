"""Thin client for the Oxylabs Amazon Scraper API — the SUPPLY side
(what is actually selling, at what price, with what reviews).

One function, `scrape(source, query, domain)`, covers every Amazon source.
The marketplace is passed explicitly (never global state) so parallel fan-out
workers on different markets never clobber each other. Live-only: Oxylabs
credentials are required.
"""
import logging

import requests

from .. import config

logger = logging.getLogger(__name__)


def scrape(source: str, query: str, domain: str | None = None, **context) -> dict:
    """Run one Oxylabs scraping job and return the parsed `content` dict.

    source: amazon_search | amazon_product | amazon_pricing | amazon_bestsellers
    query:  search keywords, a 10-character ASIN, or a category (by source)
    domain: Amazon marketplace, e.g. "in", "com", "co.uk"
    """
    if not (config.OXYLABS_USERNAME and config.OXYLABS_PASSWORD):
        raise RuntimeError(
            "OXYLABS_USERNAME / OXYLABS_PASSWORD are not set — add them to your .env"
        )

    domain = domain or config.DEFAULT_DOMAIN
    payload = {"source": source, "domain": domain, "query": query, "parse": True}
    if context:
        payload["context"] = [{"key": k, "value": v} for k, v in context.items()]

    logger.info("oxylabs live call: %s %s (%s)", source, query, domain)
    response = requests.post(
        config.OXYLABS_URL,
        auth=(config.OXYLABS_USERNAME, config.OXYLABS_PASSWORD),
        json=payload,
        timeout=90,
    )
    response.raise_for_status()
    return response.json()["results"][0]["content"]
