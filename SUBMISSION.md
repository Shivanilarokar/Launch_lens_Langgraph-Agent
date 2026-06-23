# SUBMISSION — LaunchLens

**Course:** LangGraph for Production AI Agents · **Assignment 3**
**Author:** shivani
**Repo:** _<public GitHub URL>_
**Demo video (≥2 min):** _<Loom / YouTube unlisted link>_

---

## What it is

LaunchLens is a conversational **LangGraph** agent. A founder describes a product idea;
the agent researches it **live**, **fuses demand (SerpApi) with supply (Oxylabs)**, and
returns a **Go / No-Go / Niche** verdict (demand, price band, positioning), with memory
across turns and automatic summarization.

## The 5 required LangGraph concepts (file · function · line)

1. **Graph + typed state/reducers** — `backend/src/launchlens/state.py:25` `LaunchLensState`,
   reducer `state.py:18`; wiring `backend/src/launchlens/graph.py:33` `build_graph`.
2. **Fan-out (parallel) + merge** — `backend/src/launchlens/nodes.py:196` `route_research`
   (list of `Send`) → four parallel branch nodes `nodes.py:233/238/243/248`
   (`pull_trends/pull_shopping/pull_news/pull_amazon`), merge reducer `state.py:39`.
3. **Routing (conditional edges)** — `nodes.py:156` `router`; edge `nodes.py:196` wired at `graph.py:33`.
4. **Agent node + tools** — `nodes.py:351` `agent`; ReAct loop `nodes.py:357` + `graph.py:33`;
   tools `backend/src/launchlens/tools.py:368` `ALL_TOOLS` (slim JSON).
5. **Short-term memory** — checkpointer `backend/src/launchlens/memory.py:21` `get_checkpointer`
   (Redis, SQLite fallback); summarization `nodes.py:79` `manage_memory`.

(Full table with context in `README.md`.)

## Data integration

- **SerpApi (demand):** `google_trends`, `google_shopping`, `google_news` — **3 engines**.
- **Oxylabs (supply):** `amazon_search`, `amazon_product` (review-gap mining),
  `amazon_bestsellers`, `amazon_pricing` — **4 sources**.
- The two are **fused in the agent's reasoning** (`nodes.py:254` `AGENT_PROMPT`) into one verdict.
- **Live vs mock:** runs **fully live** (both providers + LLM). No mock/fixtures — real keys
  required (see `.env.example`). The demo video shows real calls to both providers.

## How to run

```bash
cp .env.example .env      # add keys
uv sync --extra api
uv run python main.py     # CLI

# Bonus API + UI
uv run uvicorn launchlens.api.app:app --port 8010
cd frontend && npm install && npm run dev   # http://localhost:5173
```

## Deliverables checklist

- [x] Working code (CLI runs from README)
- [x] README with setup, **concept map (file+function+line)**, demo prompts
- [x] `.env.example` (no real keys committed)
- [x] Graph diagram — `docs/graph.mmd` via `graph.get_graph().draw_mermaid()` + mermaid in README
- [x] Both providers do real work, **fused**
- [x] Tools return slim JSON (token discipline)
- [ ] Slides (outline in `SLIDES.md` → export to PDF/PPT)
- [ ] 2-minute demo video (record + link above)

## Bonus implemented (+10)

- [x] **Long-term, cross-thread memory** — a LangGraph `Store` (Redis) of verdict facts;
  `agent` recalls prior research in any thread, `remember` node persists each verdict
  (`memory.py:44` `get_store`, `nodes.py:316` `_recall_facts`, `nodes.py:365` `remember`)
- [x] **FastAPI** backend with **SSE streaming** (`backend/src/launchlens/api/app.py`)
- [x] **React (Vite)** chat UI with streaming tokens, verdict cards, and a demand/supply research rail (`frontend/`)
- [x] **Redis** checkpointer (production-grade, beyond SQLite/Postgres)

## Notes

- Provider-agnostic LLM via `init_chat_model` (`LLM_MODEL` env: OpenAI or Claude).
- `reference/` (marketpulse) is a worked example only, not part of this submission.
