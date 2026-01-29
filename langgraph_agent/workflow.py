"""Temporal workflow for the research agent."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from langgraph_agent.shared import AgentInput, SleepingInput

# Activity imports must be passed through to avoid sandbox reloading
with workflow.unsafe.imports_passed_through():
    from langgraph_agent.activities import run_langgraph_agent, run_sleeping_agent


@workflow.defn
class ResearchAgentWorkflow:
    """Workflow that runs a LangGraph research agent with checkpoint recovery."""

    @workflow.run
    async def run(self, input: AgentInput) -> str:
        """Run the research agent."""
        result = await workflow.execute_activity(
            run_langgraph_agent,
            input,
            start_to_close_timeout=timedelta(minutes=10),
            heartbeat_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=5),
                backoff_coefficient=2.0,
                maximum_attempts=5,
                non_retryable_error_types=[
                    "AuthenticationError",
                    "InvalidRequestError",
                ],
            ),
        )
        return result.final_report


@workflow.defn
class SleepingAgentWorkflow:
    """Workflow that runs a sleeping agent (no checkpoint support).

    Demonstrates behavior when activity doesn't support checkpointing:
    on retry, the activity restarts from the beginning.
    """

    @workflow.run
    async def run(self, input: SleepingInput) -> int:
        """Run the sleeping agent and return steps completed."""
        result = await workflow.execute_activity(
            run_sleeping_agent,
            input,
            # Total time: sleep_seconds * num_steps (default 30s * 4 = 2 min)
            start_to_close_timeout=timedelta(minutes=5),
            # Must be > sleep_seconds to allow progress between heartbeats
            heartbeat_timeout=timedelta(seconds=45),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=5),
                backoff_coefficient=2.0,
                maximum_attempts=5,
            ),
        )
        return result.steps_completed
