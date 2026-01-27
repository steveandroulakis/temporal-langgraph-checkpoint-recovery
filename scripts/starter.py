import argparse
import asyncio
import logging
import time

from temporalio.client import Client

from order_fulfillment.shared import Order
from order_fulfillment.workflow import OrderWorkflow


async def main() -> None:
    parser = argparse.ArgumentParser(description="Start an order workflow")
    parser.add_argument("--expiry", default="12/30", help="Credit card expiry MM/YY")
    parser.add_argument(
        "--inventory-down", action="store_true", help="Simulate inventory API downtime"
    )
    parser.add_argument(
        "--pack",
        action="store_true",
        help="Include 30 items to pack (~5 min activity with heartbeat checkpoints)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    items_to_pack = [f"SKU-{i:03d}" for i in range(30)] if args.pack else []
    order = Order(
        order_id="order-1",
        item="widget",
        quantity=1,
        credit_card_expiry=args.expiry,
        items_to_pack=items_to_pack,
    )

    try:
        client = await Client.connect("localhost:7233")
        workflow_id = f"order-{order.order_id}-{int(time.time())}"
        handle = await client.start_workflow(
            OrderWorkflow.run,
            args=[order, args.inventory_down],
            id=workflow_id,
            task_queue="order-task-queue",
        )
        print(f"Started workflow with ID {workflow_id}")
        result = await handle.result()
        print(f"Result: {result}")
    except Exception as err:
        logging.error("Workflow execution failed: %s", err)
        raise SystemExit(1) from err


if __name__ == "__main__":
    asyncio.run(main())
