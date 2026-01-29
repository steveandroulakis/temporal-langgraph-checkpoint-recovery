"""Base adapter interface for Temporal agent activities."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Generic, TypeVar

from langgraph_agent.shared import AgentCheckpoint, StepResult

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class AgentAdapter(ABC, Generic[InputT, OutputT]):
    """Abstract base class for agent adapters.

    Adapters separate agent-specific logic from Temporal concerns (heartbeating,
    checkpoint restoration). The generic runner handles all Temporal interactions
    while adapters focus on executing agent logic.
    """

    @property
    @abstractmethod
    def supports_checkpointing(self) -> bool:
        """Whether this adapter supports checkpoint-based resumption."""
        ...

    @abstractmethod
    async def setup(
        self, thread_id: str, checkpoint: AgentCheckpoint | None
    ) -> None:
        """Initialize the adapter, optionally restoring from checkpoint.

        Args:
            thread_id: Unique identifier for this execution thread.
            checkpoint: Previous checkpoint to restore from, if any.
        """
        ...

    @abstractmethod
    def run(self, input: InputT) -> AsyncIterator[StepResult]:
        """Execute the agent, yielding progress after each step.

        Each yielded StepResult triggers a heartbeat. For checkpointing adapters,
        include checkpoint_id to enable resumption.

        Args:
            input: Agent-specific input data.

        Yields:
            StepResult for each completed step.
        """
        ...

    @abstractmethod
    async def get_final_output(self) -> OutputT:
        """Return the final output after run() completes.

        Returns:
            Agent-specific output data.
        """
        ...
