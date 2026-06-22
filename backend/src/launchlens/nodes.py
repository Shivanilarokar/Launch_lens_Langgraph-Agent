"""The graph's nodes — where each LangGraph concept actually lives.

  manage_memory   concept 5  summarize long threads + reset per-turn scratchpad
  router          concept 3  classify the user's intent, extract product + market
  route_research  concept 2  fan out Send() jobs across individual engines
  serpapi_worker  concept 2  one demand engine, in parallel
  oxylabs_worker  concept 2  one supply source, in parallel
  agent           concept 4  fuse demand + supply into a Go/No-Go/Niche verdict (ReAct)
"""
import json
import logging
from typing import Literal

from langchain_core.messages import HumanMessage, RemoveMessage, SystemMessage
from langgraph.graph import END
from langgraph.types import Send
from pydantic import BaseModel, Field

from . import config, tools
from .llm import get_llm
from .state import RESET, LaunchLensState

logger = logging.getLogger(__name__)

# Lazily-built models so importing this module never needs an API key.
_bound_llm = None
_plain_llm = None


def _agent_llm():
    global _bound_llm
    if _bound_llm is None:
        _bound_llm = get_llm().bind_tools(tools.ALL_TOOLS)
    return _bound_llm


def _llm():
    global _plain_llm
    if _plain_llm is None:
        _plain_llm = get_llm()
    return _plain_llm


def _last_human(messages) -> str:
    for m in reversed(messages):
        if m.type == "human" and m.content:
            return m.content
    return ""


# ───────────────────────── concept 5: memory management ───────────────────────
SUMMARY_PROMPT = """You maintain a running summary of a founder's product-research \
conversation with the LaunchLens agent.

Existing summary:
{existing}

New messages to fold in:
{convo}

Write an updated summary (max ~150 words) that preserves the concrete facts a \
later turn needs: the product idea(s), target market(s), price points discussed, \
demand/supply findings, and any verdict already given. Plain prose, no preamble."""


def _summarize(existing: str, msgs) -> str:
    convo = "\n".join(
        f"{m.type}: {m.content}" for m in msgs if getattr(m, "content", None)
    )
    prompt = SUMMARY_PROMPT.format(existing=existing or "(none)", convo=convo)
    return _llm().invoke([HumanMessage(content=prompt)]).content


def manage_memory(state: LaunchLensState) -> dict:
    """Reset the per-turn research scratchpad and, if the thread is long,
    summarize older messages and prune them (keeping the last KEEP_LAST)."""
    messages = state["messages"]
    updates: dict = {"demand_signals": RESET, "supply_signals": RESET}

    if len(messages) > config.MAX_MESSAGES:
        # Cut on a clean turn boundary (a human message) so we never orphan a
        # tool-call / tool-result pair, which the LLM API would later reject.
        cut = len(messages) - config.KEEP_LAST
        while cut < len(messages) and messages[cut].type != "human":
            cut += 1
        to_summarize = messages[:cut]
        if to_summarize:
            updates["summary"] = _summarize(state.get("summary", ""), to_summarize)
            updates["messages"] = [RemoveMessage(id=m.id) for m in to_summarize]
            logger.info("summarized %d messages", len(to_summarize))

    return updates


# ───────────────────────────── concept 3: routing ────────────────────────────
class Routing(BaseModel):
    """Structured router decision."""
    intent: Literal["full_report", "demand", "pricing", "reviews", "followup"] = Field(
        description="full_report=research a new idea end-to-end; demand=trends/interest "
        "only; pricing=price positioning; reviews=marketplace/review gaps; "
        "followup=answer from the existing conversation, no new research."
    )
    product_query: str = Field(
        default="", description="the product/idea to research, cleaned to keywords; "
        "empty for a followup that needs no new data"
    )
    domain: str = Field(
        default="in", description="Amazon market code: in, com, co.uk, de, ca, "
        "com.au, ae, co.jp"
    )


ROUTER_PROMPT = """You are the router for LaunchLens, a market-intelligence agent.
Classify the founder's latest message and extract what to research.

Current market in effect: {domain}. Known summary so far: {summary}

Rules:
- A brand-new product idea, or "should I launch X", "is X worth it" → full_report.
- Only asking about interest/trend/popularity → demand.
- Only asking about price/positioning → pricing.
- Only asking about reviews/complaints/quality → reviews.
- "what about the US market", "compare it", "why", or anything answerable from the
  conversation so far → followup (keep product_query empty).
Pick the market code from the message if the user names a country; else keep {domain}."""


def router(state: LaunchLensState) -> dict:
    last = _last_human(state["messages"])
    current_domain = state.get("domain") or config.DEFAULT_DOMAIN
    sys = SystemMessage(
        content=ROUTER_PROMPT.format(domain=current_domain, summary=state.get("summary", "") or "(none)")
    )
    try:
        decision = _llm().with_structured_output(Routing).invoke(
            [sys, HumanMessage(content=last)]
        )
        intent = decision.intent
        product_query = decision.product_query or state.get("product_query", "")
        domain = decision.domain if decision.domain in config.MARKETPLACES else current_domain
    except Exception as exc:  # noqa: BLE001 - never let routing crash a turn
        logger.warning("router fell back to heuristic: %s", exc)
        intent = "followup" if state.get("product_query") else "full_report"
        product_query = state.get("product_query", "") or last
        domain = current_domain

    logger.info("router: intent=%s domain=%s query=%r", intent, domain, product_query)
    return {"route": intent, "product_query": product_query, "domain": domain}


# ─────────────────────── concept 2: fan-out via Send ──────────────────────────
def route_research(state: LaunchLensState):
    """Conditional edge: return a LIST of Send() to run engines in PARALLEL,
    or "agent" to skip research and answer from memory."""
    route = state["route"]
    query = state.get("product_query", "")
    domain = state.get("domain", config.DEFAULT_DOMAIN)

    if route == "followup" or not query:
        return "agent"

    demand, supply = [], []
    if route in ("full_report", "demand"):
        demand = ["google_trends", "google_shopping", "google_news"]
    elif route == "pricing":
        demand = ["google_shopping"]

    if route in ("full_report", "reviews", "pricing"):
        supply = ["amazon_search"]

    if not demand and not supply:  # safety net
        demand, supply = ["google_trends"], ["amazon_search"]

    sends = [Send("serpapi_worker", {"engine": e, "query": query, "domain": domain}) for e in demand]
    sends += [Send("oxylabs_worker", {"engine": e, "query": query, "domain": domain}) for e in supply]
    logger.info("fan-out: %d demand + %d supply jobs", len(demand), len(supply))
    return sends


def serpapi_worker(payload: dict) -> dict:
    """One demand engine (runs in parallel with its siblings)."""
    engine = payload["engine"]
    try:
        signal = tools.DEMAND_ENGINES[engine](payload["query"], payload.get("domain", config.DEFAULT_DOMAIN))
    except Exception as exc:  # noqa: BLE001
        logger.exception("serpapi_worker %s failed", engine)
        signal = {"engine": engine, "error": str(exc)}
    return {"demand_signals": [signal]}


def oxylabs_worker(payload: dict) -> dict:
    """One supply source (runs in parallel with its siblings)."""
    source = payload["engine"]
    try:
        signal = tools.SUPPLY_ENGINES[source](payload["query"], payload.get("domain", config.DEFAULT_DOMAIN))
    except Exception as exc:  # noqa: BLE001
        logger.exception("oxylabs_worker %s failed", source)
        signal = {"source": source, "error": str(exc)}
    return {"supply_signals": [signal]}


# ──────────────────── concept 4: the fusing agent + tools ─────────────────────
AGENT_PROMPT = """You are LaunchLens, a market-intelligence agent for founders.
You FUSE two worlds into one answer:
  • DEMAND (Google via SerpApi): what the market wants — search trend, related
    queries, cross-retailer price band, recent news.
  • SUPPLY (Amazon via Oxylabs): what is actually selling — top products, prices,
    ratings, and review complaints (= product gaps/opportunities).

Conversation summary so far:
{summary}

DEMAND signals gathered this turn:
{demand}

SUPPLY signals gathered this turn:
{supply}

Using BOTH sides together, answer the founder. When they ask whether to launch a
product, give a clear verdict in this shape:

  VERDICT: GO / NO-GO / NICHE
  • Demand: <rising/flat/declining + the hot related searches>
  • Price band: <where their target price sits vs the market>
  • Differentiation: <gaps from review complaints they could exploit>
  • Positioning: <one or two concrete angles>

The DEMAND and SUPPLY signals above were ALREADY gathered for you this turn — treat
them as your research. Do NOT call trend_demand, shopping_prices, market_news, or
amazon_search again for the same query; answer directly from the signals above.
Only call a tool to get genuinely NEW information not shown above — e.g. amazon_pricing
for competing offers, amazon_bestsellers, or any engine for a DIFFERENT market the user
newly asks about.

GROUND DIFFERENTIATION IN REAL REVIEWS: for a launch verdict, take the top-selling ASIN
from the amazon_search results above and call `amazon_product` on it ONCE to read its
recent review complaints, then turn those concrete complaints (e.g. "leaks", "flimsy lid")
into the differentiation angle. Do not invent complaints you have not read.

Be concise and specific; cite real numbers from the signals. Never invent data."""


def _system_prompt(state: LaunchLensState) -> str:
    return AGENT_PROMPT.format(
        summary=state.get("summary", "") or "(none yet)",
        demand=json.dumps(state.get("demand_signals", []), ensure_ascii=False)[:4000] or "[]",
        supply=json.dumps(state.get("supply_signals", []), ensure_ascii=False)[:4000] or "[]",
    )


def agent(state: LaunchLensState) -> dict:
    sys = SystemMessage(content=_system_prompt(state))
    response = _agent_llm().invoke([sys] + state["messages"])
    return {"messages": [response]}


def should_continue(state: LaunchLensState):
    """Agent ⇄ tools loop: go to tools if the LLM asked for one, else finish."""
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return END
