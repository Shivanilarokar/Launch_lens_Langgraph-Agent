"""Typed graph state and its reducers.

`messages` uses LangGraph's add_messages reducer (append + honour RemoveMessage).
`demand_signals` / `supply_signals` use a custom reducer so that:
  - the parallel research workers APPEND their results (no clobbering), and
  - the memory node can RESET them to [] at the start of each turn.
Everything else overwrites (no reducer).
"""
import operator
from typing import Annotated

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

RESET = "RESET"


def reset_or_extend(current: list, update) -> list:
    """Reducer: a literal "RESET" clears the list; otherwise append (merge)."""
    if update == RESET:
        return []
    return (current or []) + list(update or [])


class LaunchLensState(TypedDict):
    # Conversation + agent/tool loop
    messages: Annotated[list, add_messages]
    # Running summary of older turns (compressed by manage_memory)
    summary: str
    # Router decision for this turn
    route: str
    # Extracted product idea and target market
    product_query: str
    domain: str
    # Founder details extracted this turn (persisted to long-term profile memory)
    user_name: str
    user_location: str
    # Research scratchpad merged from the parallel fan-out
    demand_signals: Annotated[list, reset_or_extend]
    supply_signals: Annotated[list, reset_or_extend]
    # Full display transcript — every user/assistant turn, NEVER pruned (so the chat
    # app shows the whole conversation even after summarization trims `messages`).
    transcript: Annotated[list, operator.add]
