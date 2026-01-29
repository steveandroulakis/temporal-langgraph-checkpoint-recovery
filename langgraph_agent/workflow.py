"""Temporal workflow for the research agent."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from langgraph_agent.shared import AgentInput

# Activity imports must be passed through to avoid sandbox reloading
with workflow.unsafe.imports_passed_through():
    from langgraph_agent.activities import run_langgraph_agent


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
