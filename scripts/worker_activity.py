import asyncio
import logging

from rich.logging import RichHandler
from temporalio.client import Client
from temporalio.worker import Worker

from order_fulfillment.activities import (
    deliver_order,
    pack_order_items,
    process_payment,
    reserve_inventory,
)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, handlers=[RichHandler(rich_tracebacks=True)])
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue="order-task-queue",
        workflows=[],
        activities=[
            process_payment,
            reserve_inventory,
            deliver_order,
            pack_order_items,
        ],
    )
    print("Activity-only worker started (killable for checkpoint demo)")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
