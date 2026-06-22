"""Graph construction & wiring (concept 1).

    START → manage_memory → router ─┬─(Send fan-out)→ serpapi_worker ─┐
                                    │                  oxylabs_worker ─┤
                                    └─("agent" followup)──────────────┤
                                                                      ▼
                                                          agent ⇄ tools → END
"""
import logging

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import RetryPolicy

from . import nodes, tools
from .state import LaunchLensState

logger = logging.getLogger(__name__)


def build_graph(checkpointer):
    """Build and compile the LaunchLens graph with the given checkpointer."""
    g = StateGraph(LaunchLensState)

    g.add_node("manage_memory", nodes.manage_memory)
    g.add_node("router", nodes.router)
    g.add_node("serpapi_worker", nodes.serpapi_worker,
               retry_policy=RetryPolicy(max_attempts=2))
    g.add_node("oxylabs_worker", nodes.oxylabs_worker,
               retry_policy=RetryPolicy(max_attempts=2))
    g.add_node("agent", nodes.agent)
    g.add_node("tools", ToolNode(tools.ALL_TOOLS, handle_tool_errors=True))

    g.add_edge(START, "manage_memory")
    g.add_edge("manage_memory", "router")
    # concepts 3 + 2: route to a parallel fan-out, or straight to the agent.
    g.add_conditional_edges(
        "router", nodes.route_research,
        ["serpapi_worker", "oxylabs_worker", "agent"],
    )
    g.add_edge("serpapi_worker", "agent")
    g.add_edge("oxylabs_worker", "agent")
    # concept 4: the agent ⇄ tools ReAct loop.
    g.add_conditional_edges("agent", nodes.should_continue, ["tools", END])
    g.add_edge("tools", "agent")

    return g.compile(checkpointer=checkpointer)


def draw_mermaid() -> str:
    """Return the graph as a Mermaid diagram (no checkpointer needed)."""
    return build_graph(None).get_graph().draw_mermaid()
