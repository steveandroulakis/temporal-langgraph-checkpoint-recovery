"""LangGraph adapter for Temporal agent activities."""

from collections.abc import AsyncIterator
from typing import Any

from langgraph_agent.adapters.base import AgentAdapter
from langgraph_agent.graph import build_graph, get_checkpointer
from langgraph_agent.shared import (
    AgentCheckpoint,
    AgentInput,
    AgentOutput,
    StepResult,
)


class LangGraphAdapter(AgentAdapter[AgentInput, AgentOutput]):
    """Adapter for running LangGraph research agent.

    Supports checkpoint-based resumption using LangGraph's SQLite checkpointer.
    """

    def __init__(self) -> None:
        self._thread_id: str = ""
        self._graph: Any = None
        self._config: dict[str, Any] = {}
        self._superstep_count: int = 0
        self._resuming: bool = False

    @property
    def supports_checkpointing(self) -> bool:
        return True

    async def setup(
        self, thread_id: str, checkpoint: AgentCheckpoint | None
    ) -> None:
        """Initialize graph with SQLite checkpointer.

        If checkpoint provided, LangGraph automatically resumes from that state.
        """
        self._thread_id = thread_id
        self._config = {"configurable": {"thread_id": thread_id}}

        # Restore superstep count from checkpoint
        if checkpoint:
            self._superstep_count = checkpoint.superstep_count

        # Build graph with checkpointer
        checkpointer = await get_checkpointer()
        self._graph = build_graph().compile(checkpointer=checkpointer)

        # Check if there's pending work in the checkpoint
        # If so, we should resume (pass None) instead of starting fresh
        state = await self._graph.aget_state(self._config)
        self._resuming = bool(state.next)

    async def run(self, input: AgentInput) -> AsyncIterator[StepResult]:
        """Stream graph execution, yielding StepResult per superstep."""
        # If resuming from checkpoint, pass None to continue
        # Otherwise pass fresh input to start new execution
        if self._resuming:
            stream_input = None
        else:
            stream_input = {
                "query": input.query,
                "messages": [],
                "search_results": "",
                "analysis": "",
                "final_report": "",
            }

        async for event in self._graph.astream(
            stream_input, self._config, stream_mode="updates"
        ):
            self._superstep_count += 1

            # Extract current node from event
            node_name = "unknown"
            if isinstance(event, dict):
                node_names = list(event.keys())
                if node_names:
                    node_name = node_names[0]

            # Get checkpoint_id from LangGraph state
            state = await self._graph.aget_state(self._config)
            checkpoint_id = state.config["configurable"].get("checkpoint_id")

            yield StepResult(
                step_number=self._superstep_count,
                step_name=node_name,
                checkpoint_id=checkpoint_id,
            )

    async def get_final_output(self) -> AgentOutput:
        """Return final report from graph state."""
        final_state = await self._graph.aget_state(self._config)

        final_report = ""
        if final_state.values:
            final_report = final_state.values.get("final_report", "")

        return AgentOutput(
            final_report=final_report,
            thread_id=self._thread_id,
            superstep_count=self._superstep_count,
        )
