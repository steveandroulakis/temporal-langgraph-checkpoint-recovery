"""Temporal activity for running the LangGraph agent with heartbeat checkpointing."""

import asyncio
from collections.abc import Sequence
from typing import Any

from rich.console import Console
from temporalio import activity

from langgraph_agent.graph import build_graph, get_checkpointer
from langgraph_agent.shared import AgentCheckpoint, AgentInput, AgentOutput

console = Console()


def _restore_checkpoint(heartbeat_details: Sequence[Any]) -> AgentCheckpoint | None:
    """Restore checkpoint from heartbeat details."""
    if not heartbeat_details:
        return None
    raw = heartbeat_details[0]
    if isinstance(raw, AgentCheckpoint):
        return raw
    return AgentCheckpoint(**raw)


@activity.defn
async def run_langgraph_agent(input: AgentInput) -> AgentOutput:
    """Run the LangGraph research agent with dual heartbeat pattern.

    Uses:
    1. Background heartbeat loop every 5s to keep activity alive
    2. Immediate heartbeat after each graph superstep for fine-grained recovery
    """
    info = activity.info()

    # Use workflow_id as thread_id - consistent across retries and continuations
    thread_id = info.workflow_id

    # Restore checkpoint from previous attempt if available
    checkpoint = _restore_checkpoint(info.heartbeat_details)

    if checkpoint:
        console.print(
            f"[bold yellow]⟳ RESUMING FROM CHECKPOINT[/]\n"
            f"  [dim]thread=[/]{checkpoint.thread_id}\n"
            f"  [dim]completed_supersteps=[/][cyan]{checkpoint.superstep_count}[/]\n"
            f"  [dim]last_node=[/][yellow]{checkpoint.current_node}[/]\n"
            f"  [dim]continuing from superstep[/] [bold cyan]{checkpoint.superstep_count + 1}[/]"
        )
    else:
        checkpoint = AgentCheckpoint(thread_id=thread_id)
        console.print(
            f"[bold green]★ STARTING FRESH[/] [dim]thread=[/]{thread_id}"
        )

    # Initial heartbeat to persist thread_id
    activity.heartbeat(checkpoint)

    # Set up graph with SQLite checkpointer
    checkpointer = await get_checkpointer()
    graph = build_graph().compile(checkpointer=checkpointer)

    # Background heartbeat loop
    async def heartbeat_loop() -> None:
        while True:
            await asyncio.sleep(5)
            activity.heartbeat(checkpoint)

    heartbeat_task = asyncio.create_task(heartbeat_loop())

    try:
        from langgraph.types import Command

        # Prepare config for graph execution
        config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

        # If resuming from interrupt, use Command to resume
        stream_input: dict[str, Any] | Command[Any]
        if input.resume_value is not None:
            console.print(
                f"[bold magenta]⏵ RESUMING FROM INTERRUPT[/] "
                f"[dim]value=[/][white]{input.resume_value}[/]"
            )
            stream_input = Command(resume=input.resume_value)
        else:
            stream_input = {
                "query": input.query,
                "needs_approval": input.needs_approval,
                "messages": [],
                "search_results": "",
                "analysis": "",
                "approved": False,
                "approval_feedback": "",
                "final_report": "",
            }

        final_state = None
        interrupted = False
        interrupt_value = None

        async for event in graph.astream(stream_input, config, stream_mode="updates"):  # type: ignore[arg-type]
            checkpoint.superstep_count += 1

            # Extract current node from event
            if isinstance(event, dict):
                node_names = list(event.keys())
                if node_names:
                    checkpoint.current_node = node_names[0]

            # Log node execution
            console.print(
                f"[bold cyan]▶ SUPERSTEP {checkpoint.superstep_count}[/] "
                f"[yellow]{checkpoint.current_node}[/] [dim]executed[/]"
            )

            # Extract checkpoint_id from LangGraph state
            state = await graph.aget_state(config)  # type: ignore[arg-type]
            checkpoint.checkpoint_id = state.config["configurable"].get("checkpoint_id")

            # Immediate heartbeat after superstep
            activity.heartbeat(checkpoint)

            # Log checkpoint saved
            ckpt_display = checkpoint.checkpoint_id[:8] if checkpoint.checkpoint_id else "none"
            console.print(
                f"[bold green]  ✓ checkpointed[/] [magenta]{ckpt_display}[/]"
            )

        # Get final state
        final_state = await graph.aget_state(config)  # type: ignore[arg-type]

        # Check for interrupt
        if final_state.next:
            interrupted = True
            # Get interrupt value from pending tasks
            if hasattr(final_state, "tasks") and final_state.tasks:
                for task in final_state.tasks:
                    if hasattr(task, "interrupts") and task.interrupts:
                        interrupt_value = task.interrupts[0].value
                        break
            console.print(
                f"[bold yellow]⏸ ACTIVITY PAUSED[/] "
                f"[dim]waiting for approval signal[/]"
            )

        final_report = ""
        if final_state.values:
            final_report = final_state.values.get("final_report", "")

        if not interrupted:
            console.print(
                f"[bold green]★ ACTIVITY COMPLETE[/] "
                f"[dim]supersteps=[/][cyan]{checkpoint.superstep_count}[/] "
                f"[dim]thread=[/]{thread_id}"
            )

        return AgentOutput(
            final_report=final_report,
            thread_id=thread_id,
            superstep_count=checkpoint.superstep_count,
            interrupted=interrupted,
            interrupt_value=interrupt_value,
        )

    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
