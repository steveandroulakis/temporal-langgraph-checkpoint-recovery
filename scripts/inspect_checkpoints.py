#!/usr/bin/env python3
"""Inspect LangGraph checkpoints stored in SQLite.

Usage:
    uv run scripts/inspect_checkpoints.py                # list all threads
    uv run scripts/inspect_checkpoints.py <thread_id>   # show checkpoints for thread
    uv run scripts/inspect_checkpoints.py --db path     # custom DB path
"""

import argparse
import json
import sqlite3
from pathlib import Path


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
        print("No checkpoints found in database.")
        return

    print(f"{'Thread ID':<40} Checkpoints")
    print("-" * 55)
    for thread_id, count in rows:
        print(f"{thread_id:<40} {count}")


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
        print(f"No checkpoints found for thread: {thread_id}")
        return

    print(f"Checkpoints for thread: {thread_id}")
    print("=" * 80)

    for i, (checkpoint_id, parent_id, metadata_blob) in enumerate(rows):
        print(f"\n[Step {i}]")
        print(f"  checkpoint_id: {checkpoint_id}")
        print(f"  parent_id:     {parent_id or '(none)'}")

        # Parse metadata JSON
        if metadata_blob:
            try:
                metadata = json.loads(metadata_blob)
                source = metadata.get("source", "unknown")
                step = metadata.get("step", "?")
                writes = metadata.get("writes", {})
                print(f"  source:        {source}")
                print(f"  step:          {step}")
                if writes:
                    channels = list(writes.keys())
                    print(f"  channels:      {', '.join(channels)}")
            except json.JSONDecodeError:
                print("  metadata:      (parse error)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect LangGraph checkpoints")
    parser.add_argument("thread_id", nargs="?", help="Thread ID to inspect")
    parser.add_argument(
        "--db",
        default="langgraph_checkpoints.db",
        help="Path to SQLite database (default: langgraph_checkpoints.db)",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        print("Run the checkpoint demo first to create checkpoints.")
        return

    conn = sqlite3.connect(db_path)
    try:
        if args.thread_id:
            show_thread_checkpoints(conn, args.thread_id)
        else:
            list_threads(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
