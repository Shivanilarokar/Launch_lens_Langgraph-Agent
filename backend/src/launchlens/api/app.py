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


@app.get("/threads/{thread_id}/state")
def thread_state(thread_id: str):
    vals = _state["graph"].get_state({"configurable": {"thread_id": thread_id}}).values or {}
    return {
        "thread_id": thread_id,
        "summary": vals.get("summary", ""),
        "message_count": len(vals.get("messages", [])),
    }


@app.get("/health")
def health():
    return {"status": "ok", "model": config.LLM_MODEL, "default_market": config.DEFAULT_DOMAIN}
