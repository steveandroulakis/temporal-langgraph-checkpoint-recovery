from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from order_fulfillment.activities import (
    deliver_order,
    pack_order_items,
    process_payment,
    reserve_inventory,
)
from order_fulfillment.shared import Order


@workflow.defn
class OrderWorkflow:
    """Workflow to process an order."""

    def __init__(self) -> None:
        self.approved = False

    @workflow.signal
    async def approve_order(self) -> None:
        self.approved = True

    @workflow.run
    async def run(self, order: Order, inventory_down: bool = False) -> str:
        """Run the order through payment, inventory, and delivery."""
        # Uncomment to simulate a bug in the workflow
        # raise RuntimeError("workflow bug!")

        await workflow.execute_activity(
            process_payment,
            order,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )
        await workflow.execute_activity(
            reserve_inventory,
            args=[order, inventory_down],
            start_to_close_timeout=timedelta(seconds=15),
            # No max attempts for inventory_down - let it retry until service recovers
            retry_policy=RetryPolicy()
            if inventory_down
            else RetryPolicy(maximum_attempts=1),
        )

        # Pack items if any are specified (~5 min for 30 items at 10s each)
        if order.items_to_pack:
            await workflow.execute_activity(
                pack_order_items,
                order.items_to_pack,
                start_to_close_timeout=timedelta(minutes=6),
                heartbeat_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=10),
            )

        try:
            await workflow.wait_condition(
                lambda: self.approved,
                timeout=timedelta(seconds=30),
            )
        except TimeoutError:
            return "Order expired"

        await workflow.execute_activity(
            deliver_order,
            order,
            start_to_close_timeout=timedelta(seconds=10),
        )

        return "Order fulfilled"
