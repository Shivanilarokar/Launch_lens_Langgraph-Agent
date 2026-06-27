# LaunchLens — Viva Cheat-Sheet (defend every concept)

Quick, honest answers you can give if asked to explain any part. Each points at the
real code so you can open it while answering.

---

## The 60-second pitch
"LaunchLens is a LangGraph agent that answers one question for a founder: *should I
launch this product?* It fuses **demand** (what people search/pay for, via SerpApi —
Google Trends, Shopping, News) with **supply** (what's actually selling on Amazon, via
Oxylabs — search, product reviews, pricing) and returns a **Go / No-Go / Niche** verdict.
It chats with memory, and remembers products across sessions."

---

## Concept 1 — Graph & typed state (`state.py`, `graph.py`)
**Q: How is your state designed?**
A typed `TypedDict` (`state.py:25 LaunchLensState`). `messages` uses the `add_messages`
reducer (append + honour `RemoveMessage`). `demand_signals`/`supply_signals` use a
**custom reducer** `reset_or_extend` (`state.py:18`) so parallel workers *append* but the
memory node can *reset* them each turn. Scalars (`summary`, `route`, `product_query`,
`domain`) overwrite.

**Q: Why a custom reducer instead of `operator.add`?**
`operator.add` can only append — I also need to clear the scratchpad at the start of each
turn. My reducer treats the literal `"RESET"` as "clear", anything else as "append". That
keeps fan-out merges correct *and* avoids signals leaking across turns.

**Q: Where's the wiring?** `graph.py:build_graph` — `START → manage_memory → router →
(fan-out | agent) → agent ⇄ tools → remember → END`, compiled with a checkpointer + store.

---

## Concept 2 — Fan-out / parallel (`nodes.py route_research`, workers; `graph.py`)
**Q: Show me it's really parallel, not sequential.**
`route_research` (`nodes.py:196`) returns a **list of `Send`** objects from a conditional
edge — e.g. `[Send("pull_trends", {...}), Send("pull_shopping", {...}),
Send("pull_news", {...}), Send("pull_amazon", {...})]`. Each engine is its **own node**
(`pull_trends/pull_shopping/pull_news/pull_amazon`, `nodes.py:233-248`), so the graph shows
real parallel branches. LangGraph runs all `Send`s in the **same super-step**, so they fire
concurrently and all branch edges point to `agent`, where the reducer merges their results.

**Q: What if two workers write at once?** That's exactly why the reducer exists — each
returns `{"demand_signals":[one_signal]}` and the reducer concatenates; nothing is lost.

---

## Concept 3 — Routing (`nodes.py router` + `route_research`)
**Q: How does routing work?**
`router` (`nodes.py:156`) calls the LLM with **structured output** (`Routing` pydantic
model) to classify intent into `full_report | demand | pricing | reviews | followup` and
extract the product + market. `route_research` then maps intent → which engines to fan out
(or straight to `agent` for a followup). There's a **heuristic fallback** if structured
output fails, and a safety-net default so it never dead-ends.

**Q: Give an example of the routing paying off.** "What about the US market?" → `followup`
→ skips research, answers from memory. "Is interest in X rising?" → `demand` → only the
SerpApi engines fire (saves Oxylabs credits).

---

## Concept 4 — Agent + tools (`nodes.py agent`, `tools.py`)
**Q: Walk me through the agent loop.**
`agent` (`nodes.py:351`) binds all tools (`tools.ALL_TOOLS`) to the LLM and is prompted to
**fuse** the gathered demand+supply signals into the verdict. `should_continue`
(`nodes.py:357`) sends it to the `ToolNode` if it emitted tool calls, else to `remember`.
`tools → agent` closes the ReAct loop.

**Q: Why don't tools return raw scrapes?**
Token discipline. Every tool slims the response to ~10 fields (`tools.py` `_slim_*`,
`_review_summary`) — a full Oxylabs product page is thousands of tokens; I send the dozen
that matter. Tools are also wrapped in `safe()` (`tools.py:27`) so a failure returns an
error JSON instead of crashing the graph.

**Q: How are reviews used?** For a verdict the agent calls `amazon_product` on the
top-selling ASIN to read real complaints, then turns them into the differentiation angle
(grounded, not invented).

---

## Concept 5 — Short-term memory (`memory.py get_checkpointer`, `nodes.py manage_memory`)
**Q: How does memory survive a restart?**
A **checkpointer** (`memory.py:21`) — Redis (SQLite fallback) — saves the full graph state
after every node, keyed by `thread_id`. Restart the process, pass the same `thread_id`,
and the conversation continues because the process never held the memory.

**Q: How does summarization work without breaking tool calls?**
`manage_memory` (`nodes.py:79`): when a thread passes `MAX_MESSAGES` (12), it summarizes the
older messages into `summary` and deletes them with `RemoveMessage`, keeping the last
`KEEP_LAST` (6). Crucially it cuts on a **human-message boundary**, so it never orphans an
assistant tool-call from its tool-result (which the LLM API would reject).

---

## Bonus — Long-term, cross-thread memory (`memory.py get_store`, `nodes.py remember`/`_recall_facts`)
**Q: How is this different from the checkpointer?**
The checkpointer is **per-thread** (one conversation). The **`Store`** (`memory.py:44`,
Redis) is **cross-thread** — verdict facts live under namespace `("launchlens","facts")`
and are visible in *every* thread. `remember` (`nodes.py:365`) writes each verdict;
`_recall_facts` (`nodes.py:316`) lets the agent recall it. Demo: research a product, start
a brand-new chat, ask "did we look at this before?" → it recalls without re-researching.

---

## Robustness & cost
- **Retries:** every external node (`pull_trends`, `pull_shopping`, `pull_news`,
  `pull_amazon`, `agent`, `tools`) has a `RetryPolicy` with **exponential backoff**
  (1s→2s→4s) — `graph.py RETRY`.
- **Caching:** provider responses are cached on disk with a TTL (`cache.py`,
  `CACHE_TTL`), so repeat queries don't re-spend the SerpApi free tier / Oxylabs credits.
- **Graceful degradation:** tool errors become error-JSON (`safe`), worker errors become
  error signals; the agent reasons over what it has instead of crashing.

## Scalability (the "how it scales" answer)
Stateless app (all state in Redis, keyed by `thread_id`) → run N replicas behind a load
balancer; no global mutable state (market is passed per-call); env-driven config; swap
the LLM model or backend (Redis↔SQLite↔Postgres) with no code change; bounded
context via summarization; slim JSON + caching for cost.

## If they ask "what would you improve next?"
Semantic long-term memory (vector search over past verdicts), an eval harness on tool
outputs, per-founder namespaces in the Store, and a queue in front of Oxylabs for burst load.
