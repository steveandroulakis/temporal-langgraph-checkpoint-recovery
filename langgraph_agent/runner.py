"""Generic Temporal runner for agent adapters."""

import asyncio
from collections.abc import Sequence
from typing import Any, TypeVar

from rich.console import Console
from temporalio import activity

from langgraph_agent.adapters.base import AgentAdapter
from langgraph_agent.shared import AgentCheckpoint

console = Console()

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


def _restore_checkpoint(heartbeat_details: Sequence[Any]) -> AgentCheckpoint | None:
    """Restore checkpoint from heartbeat details."""
    if not heartbeat_details:
        return None
    raw = heartbeat_details[0]
    if isinstance(raw, AgentCheckpoint):
        return raw
    return AgentCheckpoint(**raw)


async def run_adapter(
    adapter: AgentAdapter[InputT, OutputT],
    input: InputT,
    heartbeat_interval: float = 5.0,
) -> OutputT:
    """Run an adapter with Temporal heartbeating and checkpoint support.

    Handles all Temporal concerns:
    - Restore checkpoint from heartbeat_details
    - Background heartbeat loop
    - Heartbeat after each yielded step
    - Cleanup in finally block

    Args:
        adapter: The agent adapter to run.
        input: Input to pass to the adapter.
        heartbeat_interval: Seconds between background heartbeats (default 5.0).

    Returns:
        Output from the adapter.
    """
    info = activity.info()
    thread_id = info.workflow_id

    # Restore checkpoint from previous attempt
    checkpoint = _restore_checkpoint(info.heartbeat_details)

    if checkpoint and adapter.supports_checkpointing:
        next_step = checkpoint.superstep_count + 1
        console.print(
            f"[bold yellow]\u21bb RESUMING FROM CHECKPOINT[/]\n"
            f"  [dim]thread=[/]{checkpoint.thread_id}\n"
            f"  [dim]completed_steps=[/][cyan]{checkpoint.superstep_count}[/]\n"
            f"  [dim]last_node=[/][yellow]{checkpoint.current_node}[/]\n"
            f"  [dim]continuing from step[/] [bold cyan]{next_step}[/]"
        )
    elif checkpoint and not adapter.supports_checkpointing:
        console.print(
            f"[bold red]\u21bb RESTARTING (no checkpoint support)[/]\n"
            f"  [dim]thread=[/]{thread_id}\n"
            f"  [dim]adapter does not support checkpointing, starting fresh[/]"
        )
        checkpoint = None
    else:
        checkpoint = AgentCheckpoint(thread_id=thread_id)
        console.print(
            f"[bold green]\u2605 STARTING FRESH[/] [dim]thread=[/]{thread_id}"
        )

    # Initial heartbeat
    activity.heartbeat(checkpoint or AgentCheckpoint(thread_id=thread_id))

    # Setup adapter
    await adapter.setup(thread_id, checkpoint)

    # Background heartbeat loop
    current_checkpoint = checkpoint or AgentCheckpoint(thread_id=thread_id)

    async def heartbeat_loop() -> None:
        while True:
            await asyncio.sleep(heartbeat_interval)
            activity.heartbeat(current_checkpoint)

    heartbeat_task = asyncio.create_task(heartbeat_loop())

    try:
        # Run adapter and heartbeat after each step
        async for step_result in adapter.run(input):
            # Update checkpoint state
            current_checkpoint.superstep_count = step_result.step_number
            current_checkpoint.current_node = step_result.step_name
            if step_result.checkpoint_id:
                current_checkpoint.checkpoint_id = step_result.checkpoint_id

            # Log step
            console.print(
                f"[bold cyan]\u25b6 STEP {step_result.step_number}[/] "
                f"[yellow]{step_result.step_name}[/] [dim]completed[/]"
            )

            # Immediate heartbeat after step
            activity.heartbeat(current_checkpoint)

            # Log checkpoint if present
            if step_result.checkpoint_id:
                ckpt_display = step_result.checkpoint_id[:8]
                console.print(
                    f"[bold green]  \u2713 checkpointed[/] [magenta]{ckpt_display}[/]"
                )

        # Get final output
        output = await adapter.get_final_output()

        console.print(
            f"[bold green]\u2605 ACTIVITY COMPLETE[/] "
            f"[dim]steps=[/][cyan]{current_checkpoint.superstep_count}[/] "
            f"[dim]thread=[/]{thread_id}"
        )

        return output

    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
