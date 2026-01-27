import asyncio
import logging

from rich.logging import RichHandler
from temporalio.client import Client
from temporalio.worker import Worker

from order_fulfillment.workflow import OrderWorkflow


async def main() -> None:
    logging.basicConfig(level=logging.INFO, handlers=[RichHandler(rich_tracebacks=True)])
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue="order-task-queue",
        workflows=[OrderWorkflow],
        activities=[],
    )
    print("Workflow-only worker started (no activities)")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
