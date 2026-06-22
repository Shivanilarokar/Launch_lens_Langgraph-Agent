"""LaunchLens CLI — a chat loop that narrates the agent as it researches.

Run:  uv run python main.py     (or)   uv run python cli.py

Commands:
  /market <code>   switch Amazon market (in, com, co.uk, de, ca, com.au, ae, co.jp)
  /markets         list available markets
  /state           show the running summary + message count for this thread
  /new             start a fresh conversation (new thread)
  /help            show commands
  /quit            exit
"""
import logging
import sys
import uuid

# Windows legacy consoles default to cp1252 and choke on emoji / ₹ / arrows.
# Force UTF-8 so the CLI renders everywhere (and when piped/redirected).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

from langchain_core.messages import HumanMessage
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from launchlens import config, memory
from launchlens.graph import build_graph

logging.basicConfig(level=logging.WARNING)
console = Console()


def _banner(domain: str, thread_id: str):
    console.print(Panel.fit(
        "[bold cyan]LaunchLens[/] 🔭  market-intelligence agent\n"
        f"model [bold]{config.LLM_MODEL}[/]  ·  market [bold]{config.market(domain)['label']}[/]\n"
        f"thread [dim]{thread_id}[/]\n"
        "[dim]Ask: 'Should I launch a stainless-steel insulated water bottle in India under ₹1,500?'[/]\n"
        "[dim]/help for commands · /quit to exit[/]",
        border_style="cyan",
    ))


def _short(args: dict) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in list(args.items())[:3])


def _narrate(node: str, update: dict) -> str | None:
    """Print live research/tool activity; return final verdict text if present."""
    if node == "router":
        console.print(f"  [dim]· intent: {update.get('route')} → {update.get('product_query') or '(followup)'}[/]")
    elif node == "serpapi_worker":
        for s in update.get("demand_signals", []):
            eng = s.get("engine")
            if s.get("error"):
                console.print(f"  [dim red]· demand {eng}: {s['error'][:60]}[/]")
            elif eng == "google_trends":
                console.print(f"  [green]· 📈 trends[/] {s.get('trend_direction')} ({s.get('change_pct')}%) rising: {', '.join(s.get('related_rising') or []) or '—'}")
            elif eng == "google_shopping":
                b = s.get("price_band") or {}
                console.print(f"  [green]· 🛍️  shopping[/] band {b.get('min')}–{b.get('max')} ({s.get('count')} listings)")
            elif eng == "google_news":
                console.print(f"  [green]· 📰 news[/] {len(s.get('headlines') or [])} headlines")
    elif node == "oxylabs_worker":
        for s in update.get("supply_signals", []):
            src = s.get("source")
            if s.get("error"):
                console.print(f"  [dim red]· supply {src}: {s['error'][:60]}[/]")
            elif src == "amazon_search":
                console.print(f"  [yellow]· 📦 amazon[/] {len(s.get('products') or [])} top sellers")
            else:
                console.print(f"  [yellow]· 📦 {src}[/]")
    elif node == "agent":
        msg = update["messages"][-1]
        if getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                console.print(f"  [cyan]· → {tc['name']}({_short(tc.get('args', {}))})[/]")
        elif getattr(msg, "content", None):
            return msg.content
    return None


def main():
    missing = config.missing_keys()
    if missing:
        console.print(f"[red]Missing required keys in .env:[/] {', '.join(missing)}")
        console.print("[dim]Copy .env.example → .env and fill them in.[/]")
        return

    checkpointer = memory.get_checkpointer()
    graph = build_graph(checkpointer)

    domain = config.DEFAULT_DOMAIN
    thread_id = "default"
    _banner(domain, thread_id)

    try:
        while True:
            try:
                text = console.input("\n[bold]you ›[/] ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue

            # ── commands ──
            if text in ("/quit", "/exit", "/q"):
                break
            if text == "/help":
                console.print(__doc__)
                continue
            if text == "/markets":
                for code, m in config.MARKETPLACES.items():
                    console.print(f"  [bold]{code}[/] — {m['label']}")
                continue
            if text.startswith("/market"):
                parts = text.split()
                if len(parts) == 2 and parts[1] in config.MARKETPLACES:
                    domain = parts[1]
                    console.print(f"  [green]market → {config.market(domain)['label']}[/]")
                else:
                    console.print("  [red]usage: /market <code>  (see /markets)[/]")
                continue
            if text == "/new":
                thread_id = uuid.uuid4().hex[:8]
                console.print(f"  [green]new thread: {thread_id}[/]")
                continue
            if text == "/state":
                snap = graph.get_state({"configurable": {"thread_id": thread_id}})
                vals = snap.values or {}
                console.print(Panel(
                    f"messages: {len(vals.get('messages', []))}\n"
                    f"summary: {vals.get('summary') or '(none)'}",
                    title="thread state", border_style="dim",
                ))
                continue

            # ── a research/chat turn ──
            cfg = {"configurable": {"thread_id": thread_id}}
            inp = {"messages": [HumanMessage(content=text)], "domain": domain}
            final = None
            console.print("[dim]researching…[/]")
            try:
                for chunk in graph.stream(inp, cfg, stream_mode="updates"):
                    for node, update in chunk.items():
                        if update:
                            got = _narrate(node, update)
                            if got:
                                final = got
            except Exception as exc:  # noqa: BLE001
                console.print(f"[red]error: {exc}[/]")
                continue

            if final:
                console.print(Panel(Markdown(final), title="LaunchLens", border_style="cyan"))
    finally:
        memory.close()
        console.print("\n[dim]bye 👋[/]")


if __name__ == "__main__":
    main()
