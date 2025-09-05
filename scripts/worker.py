import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker
from order_fulfillment.activities import (
    process_payment,
    reserve_inventory,
    deliver_order,
)
from order_fulfillment.workflow import OrderWorkflow


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue="order-task-queue",
        workflows=[OrderWorkflow],
        activities=[process_payment, reserve_inventory, deliver_order],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
