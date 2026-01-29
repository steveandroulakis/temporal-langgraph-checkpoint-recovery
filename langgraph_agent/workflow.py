"""Temporal workflow for the research agent with interrupt handling."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

# Dataclasses are safe to import directly - they're deterministic
from langgraph_agent.shared import AgentInput, ApprovalResponse

# Activity imports must be passed through to avoid sandbox reloading
# This is the recommended pattern per Temporal docs
with workflow.unsafe.imports_passed_through():
    from langgraph_agent.activities import run_langgraph_agent


@workflow.defn
class ResearchAgentWorkflow:
    """Workflow that runs a LangGraph research agent with human-in-the-loop approval."""

    def __init__(self) -> None:
        self.approval_response: ApprovalResponse | None = None

    @workflow.signal
    async def approve_research(self, approved: bool, feedback: str = "") -> None:
        """Signal to approve or reject the research."""
        self.approval_response = ApprovalResponse(approved=approved, feedback=feedback)

    @workflow.run
    async def run(self, input: AgentInput) -> str:
        """Run the research agent, handling interrupts for human approval."""
        while True:
            # Prepare input for activity
            activity_input = AgentInput(
                query=input.query,
                needs_approval=input.needs_approval,
                resume_value=(
                    {
                        "approved": self.approval_response.approved,
                        "feedback": self.approval_response.feedback,
                    }
                    if self.approval_response
                    else None
                ),
            )

            result = await workflow.execute_activity(
                run_langgraph_agent,
                activity_input,
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

            # If not interrupted, we're done
            if not result.interrupted:
                return result.final_report

            # Log interrupt info
            workflow.logger.info(
                f"Agent interrupted for approval. "
                f"Interrupt value: {result.interrupt_value}"
            )

            # Wait for human approval signal with timeout
            try:
                await workflow.wait_condition(
                    lambda: self.approval_response is not None,
                    timeout=timedelta(minutes=30),
                )
            except TimeoutError:
                return "Research expired: approval not received within 30 minutes"

            assert self.approval_response is not None
            workflow.logger.info(
                f"Received approval: approved={self.approval_response.approved}, "
                f"feedback={self.approval_response.feedback}"
            )
