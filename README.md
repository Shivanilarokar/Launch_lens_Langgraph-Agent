# LaunchLens 🔭

**An AI market-intelligence agent that tells a founder whether a product is worth launching.**

A founder types a product idea in plain English. LaunchLens researches it **live**,
**fusing two worlds** — *demand* (Google Trends / Shopping / News via **SerpApi**) with
*supply* (Amazon search / product / pricing / bestsellers via **Oxylabs**) — and replies
with a **Go / No-Go / Niche** verdict covering demand, price band, differentiation, and
positioning. It then keeps chatting, with memory of the conversation across turns and
across sessions.

> Oxylabs tells you *what's selling*. SerpApi tells you *what the market wants*.
> LaunchLens connects them — that fusion is the whole product.

Built on **LangGraph** · Python 3.12 · provider-agnostic LLM (OpenAI or Claude) ·
**Redis** checkpointer + cross-thread store · CLI + FastAPI streaming API + React UI.

---

## Architecture

![LaunchLens graph](graph_out/graph_styled.png)

*Editable sources live in `graph_out/`: `graph_styled.mmd` (Mermaid), `launchlens_architecture.drawio`
(draw.io), and `graph_compiled.png` — generated straight from the live graph via
`graph.get_graph().draw_mermaid_png()`.*

**Every turn:** `manage_memory` (summarize / prune if the thread is long) → `router`
(classify intent) → **parallel fan-out** of research across the individual engines via
`Send` → `agent` **fuses** demand × supply — mining real Amazon reviews for the
differentiation angle — into the verdict → `remember` (persist the verdict cross-thread)
→ END. Follow-ups skip research and answer from memory, calling tools on demand.

### Data sources (live)

| Side | Provider | Used | Produces |
|------|----------|------|----------|
| Demand | SerpApi | `google_trends`, `google_shopping`, `google_news` | trend direction + related queries, cross-retailer price band, recalls / launches |
| Supply | Oxylabs | `amazon_search`, `amazon_product` (reviews), `amazon_pricing`, `amazon_bestsellers` | top sellers, prices, ratings, **review-gap mining**, competing offers |

A research turn always fires **3 demand engines in parallel** plus a **supply branch that
runs 2 Oxylabs sources** (`amazon_search` → then `amazon_product` on the top ASIN, so the
differentiation angle is grounded in *real* review snippets).

### How it scales

- **Stateless app, state in the DB:** all conversation state lives in the checkpointer
  (Redis), keyed by `thread_id` — the process holds no memory, so you can run many backend
  replicas behind a load balancer.
- **No global mutable state:** the marketplace/domain is passed explicitly through every
  tool call, so concurrent users on different markets never collide.
- **Bounded context:** the summarization node caps token growth on long threads.
- **Config via env:** keys, model, market, and Redis URI are all env-driven; swap the LLM
  (OpenAI ↔ Claude) or the checkpointer (Redis ↔ SQLite) with no code change.
- **Token discipline:** every tool returns slim JSON, never raw scrapes.
- **Resilience & cost:** every external node retries transient failures with **exponential
  backoff** (`graph.py:25` `RETRY`); provider responses are **cached** on disk with a TTL
  (`cache.py`) to spare the SerpApi free tier / Oxylabs credits.

### Memory — short-term + long-term

- **Short-term:** a **checkpointer** (`memory.py:21` `get_checkpointer`, Redis → SQLite
  fallback) that survives restarts, keyed by `thread_id`, plus a **summarization node**
  (`nodes.py:79` `manage_memory`) that compresses old turns once a thread passes a limit.
- **Long-term:** a LangGraph **`Store`** (`memory.py:44` `get_store`, Redis-backed) holding
  **facts across ALL threads** — launch verdicts and the founder's name/location. The
  `agent` reads prior verdicts (`nodes.py:346` `_recall_facts`) and the profile
  (`nodes.py:358` `_recall_profile`); the `remember` node (`nodes.py:395`) writes them.
  A verdict from one thread is recalled in a brand-new thread.

---

## The 5 LangGraph concepts → exact location

| # | Concept | Where it lives (file · function · line) |
|---|---------|------------------------------------------|
| 1 | **Typed StateGraph + reducers** | `backend/src/launchlens/state.py:25` `LaunchLensState`; custom reducer `state.py:18` `reset_or_extend`; `messages` reducer `state.py:27`; `transcript` reducer `state.py:43`; graph wiring & compile `backend/src/launchlens/graph.py:33` `build_graph` |
| 2 | **Parallel fan-out (`Send`) + merge** | conditional edge `backend/src/launchlens/nodes.py:196` `route_research` (returns a list of `Send`); four parallel branch nodes `nodes.py:233` `pull_trends`, `:238` `pull_shopping`, `:243` `pull_news`, `:248` `pull_amazon` (one super-step → merge at `agent`); merge reducer `state.py:39`; edges in `graph.py:33` `build_graph` |
| 3 | **Routing (conditional edges)** | `backend/src/launchlens/nodes.py:156` `router` (LLM intent classification → `Routing` `nodes.py:106`); conditional edge `nodes.py:196` `route_research` (intent → branches; `chitchat`/`followup` go straight to the agent) wired in `graph.py:33` |
| 4 | **Agent node + tools (ReAct)** | `backend/src/launchlens/nodes.py:381` `agent` (binds tools, fuses demand + supply); ReAct loop `nodes.py:387` `should_continue` + `graph.py`; prompt `nodes.py:274` `AGENT_PROMPT`; tools `backend/src/launchlens/tools.py:370` `ALL_TOOLS` (e.g. `tools.py:316` `trend_demand`), each wrapped by `safe` `tools.py:27` — all return **slim JSON** |
| 5 | **Short-term memory (checkpointer + summarization)** | checkpointer `backend/src/launchlens/memory.py:21` `get_checkpointer` (Redis → SQLite fallback); summarization node `backend/src/launchlens/nodes.py:79` `manage_memory` (prunes with `RemoveMessage`, cutting on a human-message boundary) |
| ★ | **Long-term, cross-thread memory (`Store`)** | `backend/src/launchlens/memory.py:44` `get_store`; read `nodes.py:346` `_recall_facts` + `nodes.py:358` `_recall_profile`; write `nodes.py:395` `remember` |

---

## Setup

Requirements: [uv](https://docs.astral.sh/uv/), Node 18+, and API keys.

```bash
# 1. Keys
cp .env.example .env        # fill in OPENAI_API_KEY, SERPAPI_API_KEY, OXYLABS_*, REDIS_URI

# 2. Backend (Python 3.12; installs the launchlens package editable, with the API extra)
uv sync --extra api

# 3. Frontend deps
cd frontend && npm install && cd ..
```

### `.env`

```ini
LLM_MODEL=openai:gpt-4o-mini          # or anthropic:claude-haiku-4-5-20251001 (+ ANTHROPIC_API_KEY)
OPENAI_API_KEY=...
SERPAPI_API_KEY=...                   # demand: Google Trends / Shopping / News
OXYLABS_USERNAME=...                  # supply: Amazon search / product / pricing / bestsellers
OXYLABS_PASSWORD=...
AMAZON_DOMAIN=in                      # default market: in, com, co.uk, de, ca, com.au, ae, co.jp
REDIS_URI=redis://default:<pw>@<host>:<port>   # Redis Cloud or local; empty → SQLite fallback
MAX_MESSAGES=12                       # summarize once a thread grows past this
KEEP_LAST=6                           # messages kept verbatim after summarizing
```

---

## Run

```bash
# CLI
uv run python main.py

# API (SSE streaming) + React UI
uv run uvicorn launchlens.api.app:app --port 8010      # terminal 1
cd frontend && npm run dev                              # terminal 2 → http://localhost:5173
```

CLI commands: `/market <code>`, `/markets`, `/state`, `/new`, `/help`, `/quit`.

---

## Demo script (shows memory across turns)

1. `Should I launch a stainless-steel insulated water bottle in India under ₹1,500?`
   → full parallel fan-out + a **Go / No-Go / Niche** verdict.
2. `What about the US market?` → recalls the idea, re-researches the `com` market.
3. `Pull the reviews of the top-selling one and name the main complaint.`
   → the agent's **ReAct tool loop** fires (calls `amazon_product`).
4. `Where would a ₹1,299 price sit vs competitors?` → pricing fusion.
5. Keep chatting until the thread passes 12 messages → the **summarization node** fires
   (`/state` shows the running summary).
6. **Quit and relaunch** (`uv run python main.py`), same thread, ask
   `What did we decide about the bottle?` → full recall from **Redis** (the checkpointer).
7. New chat, ask `Have we researched a steel water bottle before?` → recalled from the
   cross-thread **Store** (long-term memory).

---

## Evaluation

`backend/eval/` evaluates the agent on a **golden dataset of 50 fusion launch-decision
queries** (India / US / UK, varied price points) with **DeepEval**:

```bash
uv run --with deepeval python backend/eval/run_eval.py    # writes backend/eval/eval_results.md
```

Live-agent means across the 50 queries — Verdict Quality **0.85**, Data Fusion **0.76**,
Faithfulness **0.84**, Answer Relevancy **0.85** (0–1, higher is better).

---

## Project structure

```
backend/src/launchlens/   config.py llm.py state.py nodes.py graph.py memory.py tools.py cache.py
                          clients/{serpapi,oxylabs}.py   api/app.py (FastAPI SSE)
backend/eval/             golden_queries.py  run_eval.py  eval_results.md   (DeepEval harness)
backend/tests/            test_pure.py
frontend/                 Vite + React chat UI (streaming, verdict cards, research rail)
cli.py  main.py           entry points (repo root)
graph_out/                architecture diagrams (PNG · Mermaid · draw.io)
docs/                     LaunchLens-A-Market-Intelligence-System.pdf (slide deck)
reference/                worked example (marketpulse) — reference only, gitignored
```

## Notes

- **Live data:** SerpApi + Oxylabs + the LLM all run live; provider responses are cached on
  disk with a TTL (`cache.py`) to spare API quotas — toggle with `CACHE_ENABLED=false`.
- **Provider-agnostic LLM** via `init_chat_model` — switch OpenAI ↔ Claude with one env var.
- **Redis checkpointer** with an automatic **SQLite fallback** if Redis is unreachable, so
  the project always runs.

## Author

shivani
