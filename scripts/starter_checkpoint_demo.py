import asyncio
import logging
import time

from temporalio.client import Client

from order_fulfillment.shared import Order
from order_fulfillment.workflow import OrderWorkflow


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    # Create order with 10 items to pack (20s total work at 2s per item)
    items_to_pack = [f"SKU-{i:03d}" for i in range(1, 11)]
    order = Order(
        order_id="checkpoint-demo",
        item="widget",
        quantity=1,
        credit_card_expiry="12/30",
        items_to_pack=items_to_pack,
    )

    client = await Client.connect("localhost:7233")
    workflow_id = f"order-{order.order_id}-{int(time.time())}"
    handle = await client.start_workflow(
        OrderWorkflow.run,
        args=[order, False],
        id=workflow_id,
        task_queue="order-task-queue",
    )

    print(f"\nStarted workflow: {workflow_id}")
    print(f"Items to pack: {len(items_to_pack)}")
    print("\n" + "=" * 60)
    print("CHECKPOINT DEMO INSTRUCTIONS")
    print("=" * 60)
    print(
        """
1. Watch Terminal 2 (activity worker) for "Packed SKU-XXX" messages

2. After seeing "Checkpoint saved at idx=X", kill activity worker (Ctrl+C)

3. Wait ~15 seconds (heartbeat timeout will trigger retry)

4. Restart activity worker:
   uv run scripts/worker_activity.py

5. Observe: "Resuming from checkpoint idx=X" in logs

6. After packing completes, approve within 30 seconds:
   uv run scripts/signal_approve.py """
        + workflow_id
        + """

7. Workflow completes with "Order fulfilled"
"""
    )
    print("=" * 60)

    result = await handle.result()
    print(f"\nWorkflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
