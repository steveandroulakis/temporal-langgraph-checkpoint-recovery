"""Sleeping adapter for demonstrating non-checkpointing agents."""

import asyncio
from collections.abc import AsyncIterator

from langgraph_agent.adapters.base import AgentAdapter
from langgraph_agent.shared import (
    AgentCheckpoint,
    SleepingInput,
    SleepingOutput,
    StepResult,
)


class SleepingAdapter(AgentAdapter[SleepingInput, SleepingOutput]):
    """Non-checkpointing adapter that sleeps for a configurable duration.

    Demonstrates behavior when checkpoint restoration is not supported:
    on activity retry, agent restarts from the beginning.
    """

    def __init__(self) -> None:
        self._steps_completed: int = 0
        self._total_sleep_time: float = 0.0
        self._sleep_seconds: float = 30.0
        self._num_steps: int = 4

    @property
    def supports_checkpointing(self) -> bool:
        return False

    async def setup(
        self, thread_id: str, checkpoint: AgentCheckpoint | None
    ) -> None:
        """Initialize adapter. Ignores checkpoint since we don't support it."""
        del thread_id, checkpoint  # Unused - non-checkpointing adapter
        # Non-checkpointing adapter always starts fresh
        self._steps_completed = 0
        self._total_sleep_time = 0.0

    async def run(self, input: SleepingInput) -> AsyncIterator[StepResult]:
        """Sleep in steps, yielding progress after each."""
        self._sleep_seconds = input.sleep_seconds
        self._num_steps = input.num_steps

        for step in range(1, self._num_steps + 1):
            await asyncio.sleep(self._sleep_seconds)
            self._steps_completed = step
            self._total_sleep_time += self._sleep_seconds

            yield StepResult(
                step_number=step,
                step_name=f"sleep_{step}",
                checkpoint_id=None,  # No checkpointing
            )

    async def get_final_output(self) -> SleepingOutput:
        """Return final output after all steps complete."""
        return SleepingOutput(
            steps_completed=self._steps_completed,
            total_sleep_time=self._total_sleep_time,
        )
