"""Starter script for the sleeping agent demo.

This demonstrates non-checkpointing agent behavior:
1. Start the sleeping agent workflow
2. Kill the activity worker mid-execution (Ctrl+C)
3. Restart the activity worker
4. Observe: agent restarts from beginning (no checkpoint support)
"""

import argparse
import asyncio
import logging
import time

from rich.console import Console
from rich.panel import Panel
from temporalio.client import Client

from langgraph_agent.shared import SleepingInput
from langgraph_agent.workflow import SleepingAgentWorkflow


async def main() -> None:
    parser = argparse.ArgumentParser(description="Start a sleeping agent workflow")
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=30.0,
        help="Seconds to sleep per step (default: 30)",
    )
    parser.add_argument(
        "--num-steps",
        type=int,
        default=4,
        help="Number of sleep steps (default: 4)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    console = Console()

    agent_input = SleepingInput(
        sleep_seconds=args.sleep_seconds,
        num_steps=args.num_steps,
    )

    console.print(
        Panel(
            f"[bold]Sleeping Agent Demo[/]\n\n"
            f"This agent sleeps {args.sleep_seconds}s x {args.num_steps} steps.\n"
            f"It does NOT support checkpointing.\n\n"
            f"[yellow]Try this:[/]\n"
            f"1. Let it run for 1-2 steps\n"
            f"2. Kill the activity worker (Ctrl+C in its terminal)\n"
            f"3. Wait ~15s for heartbeat timeout\n"
            f"4. Restart the activity worker\n"
            f"5. Watch it restart from step 1 (no checkpoint)",
            title="Instructions",
            border_style="cyan",
        )
    )

    try:
        client = await Client.connect("localhost:7233")
        workflow_id = f"sleeping-{int(time.time())}"
        handle = await client.start_workflow(
            SleepingAgentWorkflow.run,
            agent_input,
            id=workflow_id,
            task_queue="research-agent-queue",
        )
        console.print(f"\n[bold green]Started workflow:[/] {workflow_id}")
        console.print(
            f"[dim]Config: {args.sleep_seconds}s x {args.num_steps} steps[/]"
        )

        result = await handle.result()
        console.print(
            Panel(
                f"Completed {result} steps",
                title="Sleeping Agent Complete",
                border_style="green",
            )
        )
    except Exception as err:
        logging.error("Workflow execution failed: %s", err)
        raise SystemExit(1) from err


if __name__ == "__main__":
    asyncio.run(main())
