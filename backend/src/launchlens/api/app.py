"""FastAPI layer around the LaunchLens graph (bonus: API + streaming).

Endpoints:
  POST /chat                  stream a turn as Server-Sent Events
  GET  /marketplaces          available markets
  GET  /threads               known thread ids
  GET  /threads/{id}/state    summary + message count
  GET  /health                status

Run:  uv run uvicorn launchlens.api.app:app --port 8010 --reload
"""
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from .. import config, memory
from ..graph import build_graph

logging.basicConfig(level=logging.WARNING)
_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    checkpointer = memory.get_checkpointer()
    store = memory.get_store()
    _state["graph"] = build_graph(checkpointer, store)
    _state["store"] = store
    yield
    memory.close()


app = FastAPI(title="LaunchLens API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    thread_id: str = "default"
    message: str
    domain: str | None = None


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _research_event(node: str, upd: dict) -> dict:
    if node == "router":
        return {"node": node, "route": upd.get("route"),
                "query": upd.get("product_query"), "domain": upd.get("domain")}
    if "demand_signals" in upd:  # pull_trends / pull_shopping / pull_news
        return {"node": node, "side": "demand", "signal": (upd.get("demand_signals") or [{}])[0]}
    if "supply_signals" in upd:  # pull_amazon
        return {"node": node, "side": "supply", "signal": (upd.get("supply_signals") or [{}])[0]}
    return {"node": node}


@app.post("/chat")
def chat(req: ChatRequest):
    graph = _state["graph"]
    cfg = {"configurable": {"thread_id": req.thread_id}}
    inp = {"messages": [HumanMessage(content=req.message)],
           "domain": req.domain or config.DEFAULT_DOMAIN}

    def gen():
        try:
            for mode, chunk in graph.stream(inp, cfg, stream_mode=["updates", "messages"]):
                if mode == "updates":
                    for node, upd in chunk.items():
                        if not upd:
                            continue
                        if node == "router" or node.startswith("pull_"):
                            yield _sse("research", _research_event(node, upd))
                        elif node == "agent":
                            m = upd["messages"][-1]
                            if getattr(m, "tool_calls", None):
                                yield _sse("tool", {"calls": [t["name"] for t in m.tool_calls]})
                elif mode == "messages":
                    token, meta = chunk
                    if meta.get("langgraph_node") == "agent" and getattr(token, "content", None):
                        yield _sse("token", {"text": token.content})
            vals = graph.get_state(cfg).values
            yield _sse("final", {
                "demand": vals.get("demand_signals", []),
                "supply": vals.get("supply_signals", []),
                "summary": vals.get("summary", ""),
            })
        except Exception as exc:  # noqa: BLE001
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/marketplaces")
def marketplaces():
    return {
        "default": config.DEFAULT_DOMAIN,
        "marketplaces": [{"code": c, **m} for c, m in config.MARKETPLACES.items()],
    }


@app.get("/threads")
def threads():
    return {"threads": memory.list_threads(_state["graph"].checkpointer)}


@app.get("/threads/{thread_id}/history")
def thread_history(thread_id: str):
    """Full turn-by-turn history for a thread (to reopen an older chat).

    Reads the never-pruned `transcript` so the whole conversation is shown even
    after summarization has trimmed the LLM working set (`messages`).
    """
    vals = _state["graph"].get_state({"configurable": {"thread_id": thread_id}}).values or {}
    transcript = vals.get("transcript")
    if transcript:
        return {"thread_id": thread_id, "messages": transcript}
    out = []  # fallback for threads created before the transcript existed
    for m in vals.get("messages", []):
        if m.type in ("human", "ai") and getattr(m, "content", None):
            out.append({"role": "user" if m.type == "human" else "assistant", "content": m.content})
    return {"thread_id": thread_id, "messages": out}


@app.get("/threads/{thread_id}/state")
def thread_state(thread_id: str):
    vals = _state["graph"].get_state({"configurable": {"thread_id": thread_id}}).values or {}
    return {
        "thread_id": thread_id,
        "summary": vals.get("summary", ""),
        "message_count": len(vals.get("messages", [])),
    }


@app.get("/memory")
def long_term_memory():
    """Long-term, cross-thread facts (verdicts) from the Store — accessible from any session."""
    facts = []
    try:
        for item in _state["store"].search(("launchlens", "facts"), limit=50):
            facts.append(item.value)
    except Exception:  # noqa: BLE001 - long-term memory is best-effort
        pass
    return {"facts": facts}


@app.get("/profile")
def long_term_profile():
    """The founder's remembered name / location (long-term, cross-thread)."""
    try:
        item = _state["store"].get(("launchlens", "profile"), "user")
        return {"profile": item.value if item else {}}
    except Exception:  # noqa: BLE001
        return {"profile": {}}


@app.get("/health")
def health():
    return {"status": "ok", "model": config.LLM_MODEL, "default_market": config.DEFAULT_DOMAIN}
