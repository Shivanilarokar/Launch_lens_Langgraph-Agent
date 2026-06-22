# LaunchLens — Slide Deck Outline & Demo Script

Turn this outline into slides (PDF/PPT/Google Slides), or paste it into Gamma.

---

## Slide 1 — Title
**LaunchLens 🔭** — *Should you launch this product?*
An AI agent that fuses demand + supply into a Go/No-Go verdict.
shivani · LangGraph for Production AI Agents · Assignment 3

## Slide 2 — The problem
- Founders fly blind. **Demand** data lives on Google (what people search, trends, prices).
- **Supply** data lives on marketplaces (what's selling on Amazon, at what price, with what complaints).
- Nobody connects the two. → A product looks great on demand but is saturated on supply (or vice versa).

## Slide 3 — The product
A founder chats: *"Launch a steel insulated bottle in India under ₹1,500?"*
LaunchLens answers: **GO / NO-GO / NICHE** + demand read + price band + differentiation + positioning.
…and remembers the conversation ("what about the US market?").

## Slide 4 — Data fusion (the core insight)
- **Demand · SerpApi:** Google Trends (trend + related queries), Shopping (price band), News (recalls/launches).
- **Supply · Oxylabs:** Amazon search, product (review-gap mining), bestsellers, pricing.
- Fused in the agent's reasoning → one verdict, not two features.

## Slide 5 — Architecture (LangGraph)
Show `docs/graph.mmd`:
`START → manage_memory → router → ⟨Send fan-out: trends ‖ shopping ‖ news ‖ amazon⟩ → agent ⇄ tools → END`
Call out the 5 concepts on the diagram.

## Slide 6 — The 5 concepts, mapped
1. Typed `StateGraph` + reducers (`state.py`, `graph.py`)
2. **Fan-out** via `Send` across engines, merged by a reducer (`nodes.route_research`, workers)
3. **Routing** — conditional edges by intent (`nodes.router`)
4. **Agent + tools** — ReAct loop, slim-JSON tools (`nodes.agent`, `tools.py`)
5. **Memory** — Redis checkpointer + summarization node (`memory.py`, `nodes.manage_memory`)

## Slide 7 — Engineering choices
- Provider-agnostic LLM (`init_chat_model`: OpenAI ↔ Claude, one env var).
- Live-only, slim JSON from tools (token discipline).
- Redis checkpointer (cloud) with SQLite fallback → always runs.
- Monolith: `backend/` (LangGraph + FastAPI) + `frontend/` (React).

## Slide 8 — Bonus
FastAPI **SSE streaming** API + **React** UI: streaming verdict, live demand/supply research rail.

## Slide 9 — Demo
(Switch to the live demo / video.)

## Slide 10 — Recap
Demand × Supply, fused, with memory — a founder's launch co-pilot. Thank you.

---

## 🎬 2-minute demo video script

**[0:00–0:20] Hook + problem.**
"This is LaunchLens. Founders have to guess whether a product will sell. Demand data is on
Google, supply data is on Amazon — LaunchLens fuses both and gives a Go/No-Go verdict."

**[0:20–1:00] Live run (CLI or web UI).**
Type: *"Should I launch a stainless-steel insulated water bottle in India under ₹1,500?"*
Narrate as it streams: "It's routing the intent, then **fanning out in parallel** — Google
Trends, Shopping, News, and Amazon at the same time — then fusing them." Read the verdict
(GO/NO-GO/NICHE, the trend %, price band, the review-gap differentiation).

**[1:00–1:30] Fusion + tools.**
Ask: *"Pull the reviews of the top seller and name the main complaint."* Show the agent
calling a tool (ReAct loop) and mining a real complaint into a differentiation angle.

**[1:30–2:00] Memory across turns + persistence.**
Ask: *"What about the US market?"* — it remembers the idea. Then **quit and restart**,
same thread, ask *"What did we decide about the bottle?"* → full recall from **Redis**.
Close: "Five LangGraph concepts, two live data sources, fused — that's LaunchLens."

> Record at least one real call to **each** provider on screen. Upload unlisted to
> Loom/YouTube and put the link in `README.md` and `SUBMISSION.md`.
