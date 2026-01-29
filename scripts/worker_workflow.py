import asyncio
import logging

from rich.logging import RichHandler
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import (
    SandboxedWorkflowRunner,
    SandboxRestrictions,
)

from langgraph_agent.workflow import ResearchAgentWorkflow

# Third-party modules used by activities that should be passed through
# to avoid sandbox reloading overhead (per Temporal best practices)
PASSTHROUGH_MODULES = [
    "langgraph",
    "langgraph_checkpoint",
    "langgraph_checkpoint_sqlite",
    "litellm",
    "openai",
    "httpx",
    "aiosqlite",
    "pydantic",
]


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO, handlers=[RichHandler(rich_tracebacks=True)]
    )
    client = await Client.connect("localhost:7233")

    # Configure sandbox to passthrough heavy third-party modules
    # These are deterministic and side-effect-free for our use case
    restrictions = SandboxRestrictions.default.with_passthrough_modules(
        *PASSTHROUGH_MODULES
    )

    worker = Worker(
        client,
        task_queue="research-agent-queue",
        workflows=[ResearchAgentWorkflow],
        activities=[],
        workflow_runner=SandboxedWorkflowRunner(restrictions=restrictions),
    )
    print("Workflow-only worker started (no activities)")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
