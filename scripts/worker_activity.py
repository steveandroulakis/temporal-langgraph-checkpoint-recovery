import asyncio
import logging

from rich.logging import RichHandler
from temporalio.client import Client
from temporalio.worker import Worker

from langgraph_agent.activities import run_langgraph_agent, run_sleeping_agent


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO, handlers=[RichHandler(rich_tracebacks=True)]
    )
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue="research-agent-queue",
        workflows=[],
        activities=[run_langgraph_agent, run_sleeping_agent],
    )
    print("Activity worker started (killable for checkpoint demo)")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
