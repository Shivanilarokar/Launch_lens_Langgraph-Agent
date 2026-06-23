"""The agent's tools and the research fetchers behind them.

Two audiences read this file:

  1. The LLM agent (concept 4) — it sees the `@tool` functions below and their
     DOCSTRINGS, and decides which to call during the ReAct loop for follow-ups.
  2. The fan-out workers (concept 2) — they call the plain `fetch_*` functions
     directly via the DEMAND_ENGINES / SUPPLY_ENGINES registries.

Every result is SLIMMED to the handful of fields the verdict actually needs —
never a raw scrape. Smaller tool output = cheaper, faster, sharper agents.
"""
import functools
import json
import logging
import re

from langchain_core.tools import tool

from . import config
from .clients import oxylabs as oxylabs_client
from .clients import serpapi as serpapi_client

logger = logging.getLogger(__name__)


def safe(fn):
    """A tool should RETURN an error, never raise it.

    If a tool raises mid-turn the graph can leave a thread in a broken state
    (an assistant tool-call with no tool result, which the LLM API then rejects
    on every later turn). Catching here means the agent always gets something to
    reason about and recover from.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - deliberately broad
            logger.exception("tool %s failed", fn.__name__)
            return json.dumps({"error": f"{type(exc).__name__}: {exc}"})
    return wrapper


# ─────────────────────────────── shared helpers ──────────────────────────────
def _trend_direction(series: list[float]) -> tuple[str, float | None]:
    """Classify an interest-over-time series as rising / flat / declining."""
    clean = [v for v in series if v is not None]
    if len(clean) < 2:
        return "unknown", None
    first = next((v for v in clean if v), clean[0]) or 1
    last = clean[-1]
    change = round((last - first) / first * 100, 1)
    if change > 10:
        return "rising", change
    if change < -10:
        return "declining", change
    return "flat", change


def _organic(content: dict) -> list:
    """Pull organic results out of an amazon_search response (dict or list)."""
    results = content.get("results")
    if isinstance(results, dict):
        return results.get("organic", []) or []
    if isinstance(results, list):
        return results
    return []


def _asin_from(text: str) -> str:
    """Accept a raw ASIN or a full Amazon URL and return the 10-char ASIN."""
    text = (text or "").strip()
    if re.fullmatch(r"[A-Z0-9]{10}", text):
        return text
    for pat in (r"/dp/([A-Z0-9]{10})", r"/gp/product/([A-Z0-9]{10})",
                r"/product/([A-Z0-9]{10})", r"[?&]ASIN=([A-Z0-9]{10})",
                r"\b([A-Z0-9]{10})\b"):
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return text


def _slim_search_item(item: dict) -> dict:
    return {
        "asin": item.get("asin"),
        "title": (item.get("title") or "")[:90],
        "price": item.get("price"),
        "currency": item.get("currency"),
        "rating": item.get("rating"),
        "reviews_count": item.get("reviews_count"),
        "best_seller": item.get("best_seller"),
        "sales_volume": item.get("sales_volume"),
        "image": item.get("url_image"),
    }


def _review_summary(c: dict) -> dict:
    """Rating, star distribution and a few recent review snippets — the raw
    material for mining 'what do buyers complain about' = product gaps."""
    dist = {}
    for row in c.get("rating_stars_distribution") or []:
        if row.get("rating") is not None:
            dist[f"{row['rating']}_star"] = row.get("percentage")
    snippets = []
    for rev in (c.get("reviews") or [])[:5]:
        snippets.append({
            "rating": rev.get("rating"),
            "title": (rev.get("title") or "")[:80],
            "text": (rev.get("content") or "")[:200],
        })
    return {
        "rating": c.get("rating"),
        "reviews_count": c.get("reviews_count"),
        "star_distribution": dist or None,
        "recent_reviews": snippets or None,
    }


# ══════════════════════════ DEMAND fetchers (SerpApi) ═════════════════════════
def fetch_trends(query: str, domain: str = config.DEFAULT_DOMAIN) -> dict:
    """Google Trends: interest-over-time direction + hot related queries."""
    m = config.market(domain)
    ts = serpapi_client.search(
        "google_trends", {"q": query, "geo": m["geo"], "data_type": "TIMESERIES"}
    )
    timeline = (ts.get("interest_over_time") or {}).get("timeline_data") or []
    series = []
    for pt in timeline:
        vals = pt.get("values") or []
        if vals and vals[0].get("extracted_value") is not None:
            series.append(vals[0]["extracted_value"])
    direction, change = _trend_direction(series)

    related_rising, related_top = [], []
    try:
        rq = serpapi_client.search(
            "google_trends",
            {"q": query, "geo": m["geo"], "data_type": "RELATED_QUERIES"},
        )
        rel = rq.get("related_queries") or {}
        related_rising = [r.get("query") for r in (rel.get("rising") or [])[:5]]
        related_top = [r.get("query") for r in (rel.get("top") or [])[:5]]
    except Exception:  # noqa: BLE001 - related queries are best-effort
        logger.info("related queries unavailable for %s", query)

    return {
        "engine": "google_trends",
        "query": query,
        "geo": m["geo"],
        "trend_direction": direction,
        "change_pct": change,
        "interest_start": series[0] if series else None,
        "interest_end": series[-1] if series else None,
        "related_rising": related_rising,
        "related_top": related_top,
    }


def fetch_shopping(query: str, domain: str = config.DEFAULT_DOMAIN) -> dict:
    """Google Shopping: cross-retailer price band for the product."""
    m = config.market(domain)
    data = serpapi_client.search(
        "google_shopping", {"q": query, "gl": m["gl"], "hl": m["hl"]}
    )
    items = data.get("shopping_results") or []
    prices = sorted(i["extracted_price"] for i in items if i.get("extracted_price"))
    band = None
    if prices:
        band = {
            "min": prices[0],
            "median": prices[len(prices) // 2],
            "max": prices[-1],
        }
    sample = [
        {
            "title": (i.get("title") or "")[:80],
            "price": i.get("extracted_price"),
            "source": i.get("source"),
            "rating": i.get("rating"),
        }
        for i in items[:8]
    ]
    return {
        "engine": "google_shopping",
        "query": query,
        "price_band": band,
        "count": len(items),
        "sample": sample,
    }


def fetch_news(query: str, domain: str = config.DEFAULT_DOMAIN) -> dict:
    """Google News: recent launches, recalls, competitor moves."""
    m = config.market(domain)
    data = serpapi_client.search(
        "google_news", {"q": query, "gl": m["gl"], "hl": m["hl"]}
    )
    items = data.get("news_results") or []

    def _src(i):
        s = i.get("source")
        return s.get("name") if isinstance(s, dict) else s

    headlines = [
        {
            "title": (i.get("title") or "")[:120],
            "source": _src(i),
            "date": i.get("date"),
            "snippet": (i.get("snippet") or "")[:160],
        }
        for i in items[:6]
    ]
    return {"engine": "google_news", "query": query, "headlines": headlines}


# ══════════════════════════ SUPPLY fetchers (Oxylabs) ═════════════════════════
def fetch_amazon_search(query: str, domain: str = config.DEFAULT_DOMAIN) -> dict:
    """Amazon search: top sellers with price, rating, review count."""
    content = oxylabs_client.scrape("amazon_search", query, domain)
    items = [_slim_search_item(i) for i in _organic(content) if i.get("asin")][:8]
    return {"source": "amazon_search", "query": query, "domain": domain, "products": items}


def fetch_amazon_product(asin: str, domain: str = config.DEFAULT_DOMAIN) -> dict:
    """Amazon product page: price, features, sales rank, and review gap-mining."""
    asin = _asin_from(asin)
    c = oxylabs_client.scrape("amazon_product", asin, domain, autoselect_variant=True)
    rank = None
    if isinstance(c.get("sales_rank"), list) and c["sales_rank"]:
        first = c["sales_rank"][0]
        ladder = first.get("ladder", []) if isinstance(first, dict) else []
        rank = {
            "rank": first.get("rank") if isinstance(first, dict) else None,
            "category": ladder[0]["name"] if ladder else None,
        }
    return {
        "source": "amazon_product",
        "product": {
            "asin": c.get("asin"),
            "title": (c.get("title") or "")[:120],
            "brand": c.get("brand") or c.get("manufacturer"),
            "price": c.get("price"),
            "price_strikethrough": c.get("price_initial") or None,
            "currency": c.get("currency"),
            "stock": c.get("stock"),
            "features": (c.get("bullet_points") or "")[:500],
            "sales_rank": rank,
            "reviews": _review_summary(c),
        },
    }


def fetch_amazon_bestsellers(query: str, domain: str = config.DEFAULT_DOMAIN) -> dict:
    """Amazon bestsellers for a category — what is actually selling."""
    content = oxylabs_client.scrape("amazon_bestsellers", query, domain)
    raw = content.get("results")
    if isinstance(raw, list):
        rows = raw
    elif isinstance(raw, dict):
        rows = raw.get("organic", [])
    else:
        rows = []
    items = [
        {
            "rank": r.get("rank") or r.get("pos"),
            "asin": r.get("asin"),
            "title": (r.get("title") or "")[:90],
            "price": r.get("price"),
            "rating": r.get("rating"),
        }
        for r in (rows or [])[:10]
    ]
    return {"source": "amazon_bestsellers", "query": query, "domain": domain, "bestsellers": items}


def fetch_amazon_pricing(asin: str, domain: str = config.DEFAULT_DOMAIN) -> dict:
    """Competing offers for an ASIN — where a target price would sit."""
    asin = _asin_from(asin)
    c = oxylabs_client.scrape("amazon_pricing", asin, domain)
    offers_raw = c.get("pricing") or c.get("offers") or []
    offers = [
        {
            "price": o.get("price"),
            "currency": o.get("currency"),
            "seller": o.get("seller") or o.get("seller_name"),
            "condition": o.get("condition"),
            "delivery": o.get("delivery_type") or o.get("delivery"),
        }
        for o in offers_raw[:8]
    ]
    return {"source": "amazon_pricing", "asin": asin, "domain": domain, "offers": offers}


# ════════════════════ registries used by the fan-out workers ══════════════════
# (concept 2) router dispatches Send() jobs keyed by these engine names.
DEMAND_ENGINES = {
    "google_trends": fetch_trends,
    "google_shopping": fetch_shopping,
    "google_news": fetch_news,
}
SUPPLY_ENGINES = {
    "amazon_search": fetch_amazon_search,
    "amazon_product": fetch_amazon_product,
    "amazon_bestsellers": fetch_amazon_bestsellers,
    "amazon_pricing": fetch_amazon_pricing,
}


# ═══════════════════ @tool wrappers bound to the agent (concept 4) ════════════
@tool
@safe
def trend_demand(query: str, domain: str = config.DEFAULT_DOMAIN) -> str:
    """Check market DEMAND for a product idea via Google Trends: is search
    interest rising, flat, or declining, and which related searches are hot?
    `domain` is the market: in, com, co.uk, de, ca, com.au, ae, co.jp."""
    return json.dumps(fetch_trends(query, domain))


@tool
@safe
def shopping_prices(query: str, domain: str = config.DEFAULT_DOMAIN) -> str:
    """Get the cross-retailer PRICE BAND (min/median/max) for a product via
    Google Shopping. Use to judge where a target price would sit in the market."""
    return json.dumps(fetch_shopping(query, domain))


@tool
@safe
def market_news(query: str, domain: str = config.DEFAULT_DOMAIN) -> str:
    """Scan recent NEWS for a product/category via Google News: launches,
    recalls, competitor moves. Use for landscape and risk signals."""
    return json.dumps(fetch_news(query, domain))


@tool
@safe
def amazon_search(query: str, domain: str = config.DEFAULT_DOMAIN) -> str:
    """Search Amazon for the top SELLING products by keywords: ASIN, title,
    price, rating, review count. Use first to see the marketplace reality."""
    return json.dumps(fetch_amazon_search(query, domain))


@tool
@safe
def amazon_product(asin: str, domain: str = config.DEFAULT_DOMAIN) -> str:
    """Get one Amazon product's full details + review summary (recent review
    snippets for mining complaints/gaps). Accepts a 10-char ASIN or product URL."""
    return json.dumps(fetch_amazon_product(asin, domain))


@tool
@safe
def amazon_bestsellers(query: str, domain: str = config.DEFAULT_DOMAIN) -> str:
    """List Amazon BESTSELLERS for a category to see what is actually selling."""
    return json.dumps(fetch_amazon_bestsellers(query, domain))


@tool
@safe
def amazon_pricing(asin: str, domain: str = config.DEFAULT_DOMAIN) -> str:
    """Get competing OFFERS for an ASIN (price, seller, condition) to judge
    where a target price would land. Accepts a 10-char ASIN or product URL."""
    return json.dumps(fetch_amazon_pricing(asin, domain))


ALL_TOOLS = [
    trend_demand, shopping_prices, market_news,
    amazon_search, amazon_product, amazon_bestsellers, amazon_pricing,
]
