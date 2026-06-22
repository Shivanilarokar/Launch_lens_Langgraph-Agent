"""Central configuration. Everything is read from .env at the repo root.

One source of truth for keys, model, markets, memory, and the summarization knobs.
Nothing else in the codebase reads os.environ directly.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# config.py lives at backend/src/launchlens/config.py -> repo root is 3 parents up.
REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / ".env")

# ─── LLM (provider-agnostic; init_chat_model parses "provider:model") ──────────
LLM_MODEL = os.getenv("LLM_MODEL", "openai:gpt-4o-mini")

# ─── Demand: SerpApi ──────────────────────────────────────────────────────────
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")
SERPAPI_URL = "https://serpapi.com/search.json"

# ─── Supply: Oxylabs ──────────────────────────────────────────────────────────
OXYLABS_USERNAME = os.getenv("OXYLABS_USERNAME", "")
OXYLABS_PASSWORD = os.getenv("OXYLABS_PASSWORD", "")
OXYLABS_URL = "https://realtime.oxylabs.io/v1/queries"

# ─── Markets ──────────────────────────────────────────────────────────────────
# Single source of truth for both providers:
#   - the key is the Oxylabs Amazon `domain` (supply side)
#   - `geo`/`gl`/`hl` drive SerpApi localisation (demand side)
MARKETPLACES = {
    "in":     {"label": "India · amazon.in",           "currency": "INR", "geo": "IN", "gl": "in", "hl": "en"},
    "com":    {"label": "United States · amazon.com",   "currency": "USD", "geo": "US", "gl": "us", "hl": "en"},
    "co.uk":  {"label": "United Kingdom · amazon.co.uk","currency": "GBP", "geo": "GB", "gl": "uk", "hl": "en"},
    "de":     {"label": "Germany · amazon.de",          "currency": "EUR", "geo": "DE", "gl": "de", "hl": "de"},
    "ca":     {"label": "Canada · amazon.ca",           "currency": "CAD", "geo": "CA", "gl": "ca", "hl": "en"},
    "com.au": {"label": "Australia · amazon.com.au",    "currency": "AUD", "geo": "AU", "gl": "au", "hl": "en"},
    "ae":     {"label": "UAE · amazon.ae",              "currency": "AED", "geo": "AE", "gl": "ae", "hl": "en"},
    "co.jp":  {"label": "Japan · amazon.co.jp",         "currency": "JPY", "geo": "JP", "gl": "jp", "hl": "ja"},
}

DEFAULT_DOMAIN = os.getenv("AMAZON_DOMAIN", "in")
if DEFAULT_DOMAIN not in MARKETPLACES:
    DEFAULT_DOMAIN = "in"


def market(domain: str | None = None) -> dict:
    """Return the marketplace config for a domain code, falling back to default."""
    return MARKETPLACES.get(domain or DEFAULT_DOMAIN, MARKETPLACES[DEFAULT_DOMAIN])


# ─── Memory / checkpointer ────────────────────────────────────────────────────
REDIS_URI = os.getenv("REDIS_URI", "")
SQLITE_PATH = os.getenv("SQLITE_PATH", str(REPO_ROOT / "launchlens_checkpoints.sqlite"))

# ─── Summarization knobs ──────────────────────────────────────────────────────
MAX_MESSAGES = int(os.getenv("MAX_MESSAGES", "12"))
KEEP_LAST = int(os.getenv("KEEP_LAST", "6"))


# ─── Startup validation ───────────────────────────────────────────────────────
def missing_keys() -> list[str]:
    """Return required credentials that are not configured.

    LaunchLens runs live: SerpApi (demand), Oxylabs (supply), and an LLM key.
    """
    missing: list[str] = []
    if not SERPAPI_API_KEY:
        missing.append("SERPAPI_API_KEY")
    if not (OXYLABS_USERNAME and OXYLABS_PASSWORD):
        missing.append("OXYLABS_USERNAME / OXYLABS_PASSWORD")
    provider = LLM_MODEL.split(":")[0]
    if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    return missing
