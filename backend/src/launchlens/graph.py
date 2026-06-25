"""Graph construction & wiring.

    START → manage_memory → router ─┬─(Send fan-out)→ pull_trends ──┐
                                    │                  pull_shopping ┤
                                    │                  pull_news ────┤
                                    │                  pull_amazon ──┤
                                    └─("agent" followup)─────────────┤
                                                                     ▼
                                                  agent ⇄ tools → remember → END
"""
import logging

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import RetryPolicy

from . import nodes, tools
from .state import LaunchLensState

logger = logging.getLogger(__name__)

# Exponential backoff for every node that touches an external service
# (SerpApi / Oxylabs / the LLM): retry transient failures 1s → 2s → 4s instead
# of killing the run. Non-transient errors are still surfaced.
RETRY = RetryPolicy(
    max_attempts=3,
    initial_interval=1.0,
    backoff_factor=2.0,
    max_interval=10.0,
)


def build_graph(checkpointer, store=None):
    """Build and compile the LaunchLens graph.

    checkpointer = short-term memory (per-thread). store = long-term, cross-thread
    memory — read by `agent`, written by `remember`.
    """
    g = StateGraph(LaunchLensState)

    g.add_node("manage_memory", nodes.manage_memory)
    g.add_node("router", nodes.router)
    # One node per research engine = real parallel branches in the graph.
    # External-service nodes get exponential-backoff retries on transient failures.
    PARALLEL = {
        "pull_trends": nodes.pull_trends,
        "pull_shopping": nodes.pull_shopping,
        "pull_news": nodes.pull_news,
        "pull_amazon": nodes.pull_amazon,
    }
    for name, fn in PARALLEL.items():
        g.add_node(name, fn, retry_policy=RETRY)
    g.add_node("agent", nodes.agent, retry_policy=RETRY)
    g.add_node("tools", ToolNode(tools.ALL_TOOLS, handle_tool_errors=True),
               retry_policy=RETRY)
    g.add_node("remember", nodes.remember)

    g.add_edge(START, "manage_memory")
    g.add_edge("manage_memory", "router")
    # The router fans OUT to the parallel engine nodes (Send), or straight to agent.
    g.add_conditional_edges(
        "router", nodes.route_research, [*PARALLEL.keys(), "agent"],
    )
    for name in PARALLEL:                       # every branch merges at the agent
        g.add_edge(name, "agent")
    # The agent ⇄ tools ReAct loop; on finish, persist to long-term memory.
    g.add_conditional_edges("agent", nodes.should_continue, ["tools", "remember"])
    g.add_edge("tools", "agent")
    g.add_edge("remember", END)

    return g.compile(checkpointer=checkpointer, store=store)


def draw_mermaid() -> str:
    """Return the graph as a Mermaid diagram (no checkpointer needed)."""
    return build_graph(None).get_graph().draw_mermaid()
