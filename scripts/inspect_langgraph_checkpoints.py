#!/usr/bin/env python3
"""Inspect LangGraph checkpoints stored in SQLite.

Usage:
    uv run scripts/inspect_langgraph_checkpoints.py              # list threads
    uv run scripts/inspect_langgraph_checkpoints.py <id>         # summary
    uv run scripts/inspect_langgraph_checkpoints.py <id> -d      # detailed
    uv run scripts/inspect_langgraph_checkpoints.py --db <path>  # custom DB
"""

import argparse
import asyncio
import json
import sqlite3
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

console = Console()


def list_threads(conn: sqlite3.Connection) -> None:
    """List all threads with checkpoint counts."""
    cursor = conn.execute("""
        SELECT thread_id, COUNT(*) as checkpoint_count
        FROM checkpoints
        GROUP BY thread_id
        ORDER BY MAX(rowid) DESC
    """)
    rows = cursor.fetchall()

    if not rows:
        console.print("[yellow]No checkpoints found in database.[/]")
        return

    table = Table(title="LangGraph Threads")
    table.add_column("Thread ID", style="cyan")
    table.add_column("Checkpoints", justify="right", style="green")

    for thread_id, count in rows:
        table.add_row(thread_id, str(count))

    console.print(table)
    console.print("\n[dim]Use: ... <thread_id> -d for detailed view[/]")


def show_thread_checkpoints(conn: sqlite3.Connection, thread_id: str) -> None:
    """Show checkpoint history for a specific thread."""
    cursor = conn.execute(
        """
        SELECT checkpoint_id, parent_checkpoint_id, metadata
        FROM checkpoints
        WHERE thread_id = ?
        ORDER BY rowid ASC
        """,
        (thread_id,),
    )
    rows = cursor.fetchall()

    if not rows:
        console.print(f"[red]No checkpoints found for thread: {thread_id}[/]")
        return

    console.print(Panel(f"[bold]Thread:[/] {thread_id}", border_style="blue"))

    for checkpoint_id, _parent_id, metadata_blob in rows:
        # Parse metadata
        source = "unknown"
        step = "?"
        channels: list[str] = []
        if metadata_blob:
            try:
                metadata = json.loads(metadata_blob)
                source = metadata.get("source", "unknown")
                step = metadata.get("step", "?")
                writes = metadata.get("writes", {})
                channels = list(writes.keys())
            except json.JSONDecodeError:
                pass

        # Color source based on type
        if source == "input":
            source_styled = "[blue]input[/]"
        elif source == "loop":
            source_styled = f"[yellow]{source}[/]"
        else:
            source_styled = f"[dim]{source}[/]"

        console.print(
            f"  [bold cyan]Step {step}[/] | "
            f"{source_styled} | "
            f"[dim]checkpoint:[/] {checkpoint_id[:12]}... | "
            f"[dim]channels:[/] {', '.join(channels) or '(none)'}"
        )

    console.print(f"\n[dim]Total: {len(rows)} checkpoints[/]")
    console.print("[dim]Use -d/--detailed for full node execution history[/]")


async def show_detailed_history(thread_id: str, db_path: str) -> None:
    """Show detailed node execution history using LangGraph API."""
    from langgraph_agent.graph import build_graph, get_checkpointer

    checkpointer = await get_checkpointer(db_path)
    try:
        graph = build_graph().compile(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": thread_id}}

        # Get current state
        current_state = await graph.aget_state(config)

        if not current_state.values:
            console.print(f"[red]No state found for thread: {thread_id}[/]")
            return

        # Header
        is_complete = not current_state.next
        status = "[green]Complete[/]" if is_complete else "[yellow]In Progress[/]"
        console.print(
            Panel(
                f"[bold]Thread:[/] {thread_id}\n[bold]Status:[/] {status}",
                title="Execution History",
                border_style="blue",
            )
        )

        # Build execution tree
        tree = Tree("[bold]Graph Execution[/]")

        # Collect history (comes in reverse order)
        history = []
        async for state in graph.aget_state_history(config):
            history.append(state)

        # Reverse to show chronological order
        history = list(reversed(history))

        # Map fields to node names
        field_to_node = {
            "query": "input",
            "search_results": "search",
            "analysis": "analyze",
            "final_report": "report",
        }

        # Node styling
        node_styles = {
            "input": "[blue]INPUT[/]",
            "search": "[green]search[/]",
            "analyze": "[yellow]analyze[/]",
            "report": "[magenta]report[/]",
        }

        # Track which fields we've seen to detect new ones
        prev_fields: set[str] = set()

        for state in history:
            metadata = state.metadata or {}
            step = metadata.get("step", 0)

            # Find which fields are newly populated in this step
            current_fields: set[str] = set()
            for key in ["query", "search_results", "analysis", "final_report"]:
                value = state.values.get(key, "")
                if isinstance(value, str) and value:
                    current_fields.add(key)

            new_fields = current_fields - prev_fields
            prev_fields = current_fields

            # Determine which node ran based on new fields
            for field in new_fields:
                node_name = field_to_node.get(field, "unknown")
                node_label = node_styles.get(node_name, f"[cyan]{node_name}[/]")

                branch = tree.add(f"{node_label} [dim]step {step}[/]")

                # Show output preview
                value = state.values.get(field, "")
                if value:
                    preview = value[:80].replace("\n", " ")
                    if len(value) > 80:
                        preview += "..."
                    branch.add(f"[dim]{field}:[/] {preview}")

        console.print(tree)

        # Show state summary
        console.print()
        final_values = current_state.values

        # Create summary table
        table = Table(title="State", show_header=True, header_style="bold")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white", max_width=60)

        for key in ["query", "search_results", "analysis", "final_report"]:
            value = final_values.get(key, "")
            if value:
                # Truncate for display
                display = value[:100].replace("\n", " ")
                if len(value) > 100:
                    display += f"... ({len(value)} chars)"
                table.add_row(key, display)

        console.print(table)

        # Show next nodes if not complete
        if current_state.next:
            next_nodes = ", ".join(current_state.next)
            console.print(f"\n[yellow]Next nodes to execute:[/] {next_nodes}")

    finally:
        # Properly close the aiosqlite connection
        await checkpointer.conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect LangGraph checkpoints")
    parser.add_argument("thread_id", nargs="?", help="Thread ID to inspect")
    parser.add_argument(
        "-d",
        "--detailed",
        action="store_true",
        help="Show detailed node execution history",
    )
    parser.add_argument(
        "--db",
        default="langgraph_checkpoints.db",
        help="Path to SQLite database (default: langgraph_checkpoints.db)",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        console.print(f"[red]Database not found: {db_path}[/]")
        console.print("[dim]Run the checkpoint demo first to create checkpoints.[/]")
        return

    if args.thread_id and args.detailed:
        # Use async LangGraph API for detailed view
        asyncio.run(show_detailed_history(args.thread_id, str(db_path)))
    elif args.thread_id:
        conn = sqlite3.connect(db_path)
        try:
            show_thread_checkpoints(conn, args.thread_id)
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(db_path)
        try:
            list_threads(conn)
        finally:
            conn.close()


if __name__ == "__main__":
    main()
