# Submission - Assignment 3

**Student(s):** shivani
**GitHub repo:** https://github.com/Shivanilarokar/Launch_lens_Langgraph-Agent
**Live app:** https://launch-lens-langgraph-agent.vercel.app  (API: https://launchlenslanggraph-agent-production.up.railway.app)
**Demo video (≥2 min):** [`demo/LaunchLens-demo.mp4`](demo/LaunchLens-demo.mp4)
**Presentation / slides:** [`Deck/LaunchLens-A-Market-Intelligence-System.pdf`](Deck/LaunchLens-A-Market-Intelligence-System.pdf)

---

## 1. LaunchLens in your words (2-3 sentences)

LaunchLens is a conversational LangGraph agent that tells a founder whether a product is
worth launching. It pulls **demand** signals from Google via SerpApi (Trends, Shopping,
News) and **supply** signals from Amazon via Oxylabs (search, product reviews, pricing,
bestsellers) **in parallel**, then the agent fuses both sides into a single **Go / No-Go /
Niche** verdict with a price band, a differentiation angle mined from real review
complaints, and positioning — and it remembers the conversation across turns and sessions.

---

## 2. Concept map - where each required concept lives

| Concept | File | Function / node | Line(s) | One-line note |
|---------|------|-----------------|---------|---------------|
| Graph & state | `backend/src/launchlens/state.py` · `graph.py` | `LaunchLensState` · `build_graph` | `state.py:25` · `graph.py:33` | Typed `StateGraph` + custom reducers (`reset_or_extend` `state.py:18`) |
| Fan-out (parallel) | `backend/src/launchlens/nodes.py` | `route_research` → `pull_trends/shopping/news/amazon` | `nodes.py:196` (→ `:233/:238/:243/:248`) | Returns a list of `Send`; 4 engines run in one super-step, merged by a reducer |
| Routing (conditional edges) | `backend/src/launchlens/nodes.py` | `router` (+ `Routing`) → `route_research` | `nodes.py:156` (`Routing` `:106`) | LLM classifies intent; conditional edge picks branches vs straight-to-agent |
| Agent node + tools | `backend/src/launchlens/nodes.py` · `tools.py` | `agent` · `should_continue` · `ALL_TOOLS` | `nodes.py:381` · `:387` · `tools.py:370` | ReAct loop; fuses demand+supply; 7 slim-JSON tools (`AGENT_PROMPT` `nodes.py:274`) |
| Short-term memory (checkpointer + summarization) | `backend/src/launchlens/memory.py` · `nodes.py` | `get_checkpointer` · `manage_memory` | `memory.py:21` · `nodes.py:79` | Redis→SQLite checkpointer + summarization node that prunes on a human-message boundary |
| **Bonus — long-term cross-thread memory** | `backend/src/launchlens/memory.py` · `nodes.py` | `get_store` · `_recall_facts`/`_recall_profile` · `remember` | `memory.py:44` · `nodes.py:346/358` · `:395` | LangGraph `Store` keeps verdicts + founder profile across ALL threads |

---

## 3. Data sources used

- **SerpApi engine(s):** `google_trends` (trend direction + rising related queries),
  `google_shopping` (cross-retailer price band), `google_news` (launches / recalls) —
  used for the **demand** read.
- **Oxylabs source(s):** `amazon_search` (top sellers, prices, ratings), `amazon_product`
  (review-gap mining on the top ASIN), plus `amazon_pricing` and `amazon_bestsellers`
  available to the agent — used for the **supply** read.
- **How they combine:** the agent node fuses demand × supply in one prompt — is interest
  rising, where does the target price sit, and what review complaints can be exploited —
  into a single Go/No-Go/Niche verdict.
- **Live vs mocked:** everything is a **live API call** (SerpApi + Oxylabs + the LLM);
  nothing is mocked. Responses are cached on disk with a TTL (`cache.py`) only to spare
  API quotas on repeat queries.

---

## 4. How to run

```bash
# setup
cp .env.example .env        # fill OPENAI_API_KEY, SERPAPI_API_KEY, OXYLABS_*, REDIS_URI
uv sync --extra api         # Python 3.12, installs the launchlens package + API extras
cd frontend && npm install && cd ..

# run the CLI
uv run python main.py

# run the API (SSE streaming) + React UI
uv run uvicorn launchlens.api.app:app --port 8010    # terminal 1
cd frontend && npm run dev                            # terminal 2 -> http://localhost:5173
```

Or just open the live app: **https://launch-lens-langgraph-agent.vercel.app**

---

## 5. Demo script (the prompts in your recording)

1. `Should I launch a stainless-steel insulated water bottle in India under ₹1,500?`
   → full parallel fan-out → a Go/No-Go/Niche verdict.
2. `What about the US market?` → recalls the idea, re-researches the US.
3. `Pull the reviews of the top-selling one and name the main complaint.`
   → the agent's ReAct tool loop fires (`amazon_product`).
4. `Where would a ₹1,299 price sit vs competitors?` → pricing fusion.
5. After 12+ messages the summarization node fires (`/state` shows the running summary);
   quit and relaunch the same thread → full recall from Redis (checkpointer).
6. New chat: `Have we researched a steel water bottle before?` → recalled from the
   cross-thread `Store` (long-term memory).

---

## 6. Bonus attempted (if any)

- **Long-term, cross-thread memory** — LangGraph `Store` persists verdicts + the founder's
  profile (`memory.py:44`, `nodes.py:395`).
- **Evaluation** — DeepEval on a golden dataset of **50 fusion launch-decision queries**
  (IN/US/UK); means: Verdict Quality 0.85, Data Fusion 0.76, Faithfulness 0.84,
  Answer Relevancy 0.85 (`backend/eval/`, results in `backend/eval/eval_results.md`).
- **FastAPI SSE streaming API + React UI** — streaming verdict, live demand/supply
  research rail, multi-session sidebar, long-term memory pane (`api/app.py`, `frontend/`).
- **Live deployment** — frontend on Vercel, backend on Railway, Redis on Redis Cloud.
- **Resilience** — exponential-backoff retries on every external node + on-disk response cache.

---

## 7. Known limitations / what I'd do next

- **API quotas:** the SerpApi free tier (~250/month) limits how many fresh research turns
  the public demo can serve; a production build would add caching tiers + per-IP rate limits.
- **Trend signal nuance:** Google Trends returns relative interest, so very new niche terms
  can read as "unknown"; I'd blend in marketplace sales-rank velocity for those.
- **Demo timing:** the video's scene timing is aligned to the narration by transcript
  timestamps; a forced-alignment pass would make it frame-perfect.
- **Next:** a watchlist that re-runs a verdict on a schedule and alerts when demand or price
  shifts, plus competitor-level price tracking over time.
